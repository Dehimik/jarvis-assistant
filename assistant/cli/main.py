from __future__ import annotations
import argparse
import json
import queue
import sys
import threading
from typing import Optional

import uvicorn
import sounddevice as sd
from vosk import Model, KaldiRecognizer

from assistant.bus.client import BusClient
from assistant.telemetry.log import setup_logger

log = setup_logger(app_name="jarvis", level="ERROR", env="dev", serialize=False)


# ================== AUDIO / STT ==================
class MicSTT:
    def __init__(self, model_path: str, samplerate: int = 44100, device: Optional[int] = None, blocksize: int = 11025):
        """
        samplerate: 16000 рекомендується Vosk-ом (менше латентність).
        blocksize: 4000 ~ 0.25s при 16кГц; зменшуй для меншої затримки.
        """
        self.model = Model(model_path)
        self.rec = KaldiRecognizer(self.model, samplerate)
        self.q: "queue.Queue[bytes]" = queue.Queue()
        self.device = device
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.stream: Optional[sd.RawInputStream] = None

    def _callback(self, indata, frames, time, status):
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        self.q.put(bytes(indata))

    def start(self):
        self.stream = sd.RawInputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            device=self.device,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()

    def results(self):
        """Генератор, що віддає фінальні текстові результати Vosk."""
        while True:
            data = self.q.get()
            if self.rec.AcceptWaveform(data):
                res = json.loads(self.rec.Result())
                txt = (res.get("text") or "").strip()
                if txt:
                    yield txt
            # else:
            #     partial = json.loads(self.rec.PartialResult()).get("partial", "")


# ================== HELPERS ==================
def list_input_devices() -> None:
    print("== Вхідні пристрої ==")
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            sr = int(dev["default_samplerate"])
            print(f"[{idx}] {dev['name']}  (in: {dev['max_input_channels']}, sr: {sr})")


# ================== RUNNERS ==================
def run_daemon(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run("assistant.bus.server:app", host=host, port=port, reload=False, workers=1)


def run_cli():
    parser = argparse.ArgumentParser(prog="va-cli", description="Voice Assistant CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # text → NLU
    p_parse = sub.add_parser("parse", help="Parse text via NLU (and execute via plugins)")
    p_parse.add_argument("text", type=str, help="Text to parse")

    # reload NLU
    sub.add_parser("reload-nlu", help="Reload YAML intents")

    # voice → NLU
    p_listen = sub.add_parser("listen", help="Listen from mic, transcribe with Vosk, send to NLU")
    p_listen.add_argument("--model", help="Path to Vosk model folder (contains model.conf)")
    p_listen.add_argument("--device", type=int, default=None, help="Audio input device index")
    p_listen.add_argument("--samplerate", type=int, default=16000, help="Sample rate for capture (recommended 16000)")
    p_listen.add_argument("--blocksize", type=int, default=4000, help="Audio block size for lower latency")
    p_listen.add_argument("--list-devices", action="store_true", help="List audio input devices and exit")
    p_listen.add_argument("--print-intents", action="store_true", help="Print NLU intents for each utterance")
    p_listen.add_argument("--exit-phrases", nargs="*", default=["вийти", "стоп", "зупинись"], help="Phrases to stop loop")

    # server/common
    p_host = parser.add_argument_group("server")
    p_host.add_argument("--url", default="http://127.0.0.1:8000", help="Bus base URL")

    args = parser.parse_args()
    c = BusClient(base_url=args.url)

    if args.cmd == "parse":
        res = c.parse(args.text)
        if not res.get("ok"):
            # log.error(res)
            print("ERR:", res.get("error"))
            raise SystemExit(1)
        print(f"intent={res['intent']} slots={res['slots']} conf={res['confidence']}")
        if "action" in res:
            print("action:", res["action"])

    elif args.cmd == "reload-nlu":
        res = c.reload_nlu()
        print("ok" if res.get("ok") else res)

    elif args.cmd == "listen":
        if args.list_devices:
            list_input_devices()
            return

        # валідація аудіо налаштувань перед запуском
        try:
            sd.check_input_settings(device=args.device, samplerate=args.samplerate, channels=1, dtype="int16")
        except Exception as e:
            print(f"Помилка аудіо-налаштувань: {e}", file=sys.stderr)
            raise SystemExit(2)

        stt = MicSTT(model_path=args.model, samplerate=args.samplerate, device=args.device, blocksize=args.blocksize)
        stt.start()
        print("🎙️  Слухаю... (Ctrl+C для виходу)")
        if args.device is not None:
            print(f"Пристрій: {args.device}")
        try:
            for text in stt.results():
                print(f"\n👂 Розпізнано: «{text}»")

                # простий вихід по ключовим фразам
                if any(text.endswith(p) or text == p for p in args.exit_phrases):
                    print("Завершення за командою користувача.")
                    break

                # відправляємо у твій NLU-сервер
                try:
                    res = c.parse(text)
                except Exception as e:
                    print(f"ERR: не вдалося звернутись до NLU: {e}", file=sys.stderr)
                    continue

                if not res.get("ok"):
                    # log.error(res)
                    print("ERR:", res.get("error"))
                    continue

                if args.print_intents:
                    print(f"intent={res['intent']} slots={res['slots']} conf={res['confidence']}")

                # якщо сервер повертає підказку до дії — покажемо
                if "action" in res:
                    print("action:", res["action"])
        except KeyboardInterrupt:
            print("\nЗавершення…")
        finally:
            stt.stop()

if __name__ == "__main__":
    run_cli()
