# assistant/main.py
from __future__ import annotations
import argparse
import sys
from typing import Optional

import sounddevice as sd
import numpy as np
import uvicorn

from assistant.bus.client import BusClient
from assistant.telemetry.log import setup_logger

# core modules
from assistant.config.resolver import ConfigResolver
from assistant.audio.recorder import recorder_ctx  # PvRecorder-обгортка: start/read/stop/release

# init logger
log = setup_logger(app_name="jarvis", level="ERROR", env="dev", serialize=False)

def play_pcm_s16le(data: bytes, sample_rate: int = 22050):
    """PLay PCM s16le from bytes"""
    if not data:
        return
    arr = np.frombuffer(data, dtype=np.int16)
    sd.play(arr, samplerate=sample_rate)
    sd.wait()

# ================== HELPERS ==================
def list_input_devices() -> None:
    """List input devices using sounddevice"""
    print("== Вхідні пристрої ==")
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            sr = int(dev.get("default_samplerate", 0))
            print(f"[{idx}] {dev.get('name','?')}  (in: {dev.get('max_input_channels')}, sr: {sr})")

def check_audio_settings(device: Optional[int]) -> None:
    """Quick validation for channel (mono int16). PvRecorder works on 16kHz; theres only sanity-check"""
    try:
        sd.check_input_settings(device=device, samplerate=16000, channels=1, dtype="int16")
    except Exception as e:
        print(f"Помилка аудіо-налаштувань: {e}", file=sys.stderr)
        raise SystemExit(2)

# ================== RUNNERS ==================
def run_daemon(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run("assistant.bus.server:app", host=host, port=port, reload=False, workers=1)

def run_cli():
    parser = argparse.ArgumentParser(prog="va-cli", description="Voice Assistant CLI (plugins + YAML config)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # text → NLU
    p_parse = sub.add_parser("parse", help="Parse text via NLU (and execute via plugins)")
    p_parse.add_argument("text", type=str, help="Text to parse")

    # reload NLU
    sub.add_parser("reload-nlu", help="Reload YAML intents")

    # voice → NLU
    p_listen = sub.add_parser("listen", help="Listen from mic, transcribe via STT plugin, send to NLU")
    p_listen.add_argument("--config", default="assistant/config/config.yaml", help="Path to YAML config (stt/tts)")
    p_listen.add_argument("--plugins-dir", default="configs/plugins.d/voice", help="Directory with STT/TTS plugins")
    p_listen.add_argument("--device", type=int, default=None, help="Audio input device index (mic)")
    p_listen.add_argument("--frame", type=int, default=512, help="Frame length for Recorder.read()")
    p_listen.add_argument("--list-devices", action="store_true", help="List audio input devices and exit")
    p_listen.add_argument("--print-intents", action="store_true", help="Print NLU intents for each utterance")
    p_listen.add_argument("--say-ok", action="store_true", help="Say after intent parsing")
    p_listen.add_argument("--exit-phrases", nargs="*", default=["вийти", "стоп", "зупинись"],
                          help="Phrases to stop loop")

    # server/common
    p_host = parser.add_argument_group("server")
    p_host.add_argument("--url", default="http://127.0.0.1:8000", help="Bus base URL")

    args = parser.parse_args()
    c = BusClient(base_url=args.url)

    # for parsing from text
    if args.cmd == "parse":
        res = c.parse(args.text)
        if not res.get("ok"):
            print("ERR:", res.get("error"))
            raise SystemExit(1)
        print(f"intent={res['intent']} slots={res['slots']} conf={res['confidence']}")
        if "action" in res:
            print("action:", res["action"])
        return

    # for reload nlu without stopping server
    if args.cmd == "reload-nlu":
        res = c.reload_nlu()
        print("ok" if res.get("ok") else res)
        return

    # for listening
    if args.cmd == "listen":
        if args.list_devices:
            list_input_devices()
            return

        # download plugins from yaml
        resolver = ConfigResolver(config_path=args.config, plugins_dir=args.plugins_dir)
        try:
            plugins = resolver.resolve_all()
        except Exception as e:
            log.exception(e)
            print(f"ERR: не вдалося завантажити конфіг/плагіни: {e}", file=sys.stderr)
            raise SystemExit(3)

        stt = plugins["stt"]          # STTPlugin: .sample_rate(), .accept(pcm)->dict|None, .partial()
        tts = plugins["tts"]          # TTSPlugin: .sample_rate(), .synth(text)->bytes (не обов'язково використовувати)

        # sanity-check audio
        check_audio_settings(args.device)

        # start micro
        with recorder_ctx(device_index=(args.device if args.device is not None else 0),
                                   frame_length=args.frame) as rec:
            dev_name = rec.start()
            print(f"🎙️  Listening... (Ctrl+C for exit)")
            print(f"Device: {dev_name} | STT={stt.__class__.__name__}")

            # main loop: read frames → STT → NLU
            try:
                while True:
                    pcm = rec.read()          # list[int16], length = frame_length
                    res = stt.accept(pcm)     # dict | None (final result)
                    if not res:
                        continue

                    text = (res.get("text") or "").strip()
                    if not text:
                        continue

                    print(f"\n👂 Розпізнано: «{text}»")

                    # exit phrases
                    if any(text.endswith(p) or text == p for p in args.exit_phrases):
                        print("Завершення за командою користувача.")
                        break

                    # parse in NLU
                    try:
                        nlu = c.parse(text)
                    except Exception as e:
                        print(f"ERR: не вдалося звернутись до NLU: {e}", file=sys.stderr)
                        continue

                    if not nlu.get("ok"):
                        print("ERR:", nlu.get("error"))
                        continue

                    if args.print_intents:
                        print(f"intent={nlu['intent']} slots={nlu['slots']} conf={nlu['confidence']}")

                    if "action" in nlu:
                        print("action:", nlu["action"])

                    if "reply" in nlu:
                        print("reply:", nlu["reply"])

                    if args.say_ok:
                        reply = nlu.get("reply")
                        if reply:
                            pcm_out = tts.synth(reply)
                            play_pcm_s16le(pcm_out, tts.sample_rate())

            except KeyboardInterrupt:
                print("\nЗавершення…")
            # Recorder context will himself call stop()/release()
        return


if __name__ == "__main__":
    run_cli()
