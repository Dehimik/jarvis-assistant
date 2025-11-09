from __future__ import annotations
import argparse
import asyncio
import sys
from typing import Optional

import sounddevice as sd
import numpy as np
import time
from pathlib import Path

import uvicorn

# --- твої модулі ---
from assistant.bus.client import BusClient
from assistant.telemetry.log import setup_logger

# stt tts
from assistant.config.resolver import ConfigResolver
from assistant.audio.recorder import recorder_ctx

# PATH
HERE = Path(__file__).resolve().parent           # assistant/
REPO = HERE.parent                               # корінь репо (де assistant/ та gui/)
DEFAULT_CONFIG = HERE / "config" / "config.yaml" # assistant/config/config.yaml
DEFAULT_PLUGINS = REPO / "configs" / "plugins.d" / "voice"
LOG_FILE = REPO / "assistant" / "data" / "jarvis.log"

# helpers
def play_pcm_s16le(data: bytes, sample_rate: int = 22050):
    """PLay PCM s16le from bytes"""
    if not data:
        return
    arr = np.frombuffer(data, dtype=np.int16)
    sd.play(arr, samplerate=sample_rate)
    sd.wait()

def check_audio_settings(device: Optional[int]) -> None:
    """Quick validation for channel (mono int16). PvRecorder works on 16kHz; theres only sanity-check"""
    try:
        sd.check_input_settings(device=device, samplerate=16000, channels=1, dtype="int16")
    except Exception as e:
        print(f"Помилка аудіо-налаштувань: {e}", file=sys.stderr)
        raise SystemExit(2)

def list_input_devices() -> None:
    """List input devices using sounddevice"""
    print("== Вхідні пристрої ==")
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            sr = int(dev.get("default_samplerate", 0))
            print(f"[{idx}] {dev.get('name','?')}  (in: {dev.get('max_input_channels')}, sr: {sr})")

def _resolve_path(p: str | Path, *fallbacks: Path) -> Path:
    p = Path(p)
    if p.is_absolute():
        return p
    # перевіряємо кілька кандидатів: CWD, поруч із main.py, корінь репо та фолбеки
    candidates = [Path.cwd() / p, HERE / p, REPO / p, *fallbacks]
    for c in candidates:
        if c.exists():
            return c
    # якщо нічого не знайшли — повернемо шлях біля main.py (щоб було передбачувано)
    return (HERE / p)

# server runner
def run_daemon(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run("assistant.bus.server:app", host=host, port=port, reload=False, workers=1)

# main runner
def main():
    parser = argparse.ArgumentParser(description="Jarvis voice assistant CLI")
    sub = parser.add_subparsers(dest="cmd")

    # --- voice listen ---
    listen_p = sub.add_parser("listen", help="Run continuous listening loop")
    listen_p.add_argument("--config", type=str, default=str(DEFAULT_CONFIG))
    listen_p.add_argument("--plugins-dir", type=str, default=str(DEFAULT_PLUGINS))
    listen_p.add_argument("--url", type=str, default="http://127.0.0.1:8000")
    listen_p.add_argument("--list-devices", action="store_true", help="List audio input devices and exit")
    listen_p.add_argument("--device", type=str, default=None, help="microphone device name or index")
    listen_p.add_argument("--frame", type=int, default=512)
    listen_p.add_argument("--print-intents", action="store_true")
    listen_p.add_argument("--say-ok", action="store_true")

    args = parser.parse_args()

    if args.cmd == "listen":
        asyncio.run(run_listen(args))
    else:
        parser.print_help()


# =========================================================
#                 LISTEN LOOP
# =========================================================
async def run_listen(args):
    """
    Основний цикл:
    1) Завантажує плагіни з YAML (STT/TTS)
    2) Перевіряє аудіо
    3) Стартує рекордер і читає PCM-фрейми
    4) STT.accept(pcm) -> fin.результат → NLU (через BusClient)
    5) Відтворює TTS (опційно), обробляє exit-фрази
    """

    cfg_path = _resolve_path(args.config, DEFAULT_CONFIG)
    plugins_dir = _resolve_path(args.plugins_dir, DEFAULT_PLUGINS)

    log = setup_logger("jarvis", level="INFO", env="dev", serialize=False)
    log.info("🎙️  Jarvis is starting...")

    # клієнт до NLU/Bus
    c = BusClient(base_url=args.url)

    if args.list_devices:
        list_input_devices()
        return

    # download plugins from yaml
    resolver = ConfigResolver(config_path=cfg_path, plugins_dir=plugins_dir)
    try:
        plugins = resolver.resolve_all()
    except Exception as e:
        log.exception(e)
        print(f"ERR: не вдалося завантажити конфіг/плагіни: {e}", file=sys.stderr)
        raise SystemExit(3)

    stt = plugins["stt"]          # STTPlugin: .sample_rate(), .accept(pcm)->dict|None, .partial()
    tts = plugins["tts"]          # TTSPlugin: .sample_rate(), .synth(text)->bytes (може бути необов'язковий)

    # sanity-check audio
    check_audio_settings(args.device)

    # список вихідних фраз (якщо не передали — порожній)
    exit_phrases = getattr(args, "exit_phrases", [])

    # start micro
    with recorder_ctx(
        device_index=(args.device if args.device is not None else 0),
        frame_length=args.frame
    ) as rec:
        dev_name = rec.start()
        log.info(f"Listening... (Ctrl+C for exit)")
        log.info(f"Device: {dev_name} | STT={stt.__class__.__name__}")

        # main loop: read frames → STT → NLU
        try:
            while True:
                pcm = rec.read()              # list[int16], length = frame_length
                res = stt.accept(pcm)         # dict | None (final result)
                if not res:
                    continue

                text = (res.get("text") or "").strip()
                if not text:
                    continue

                log.info(f"\nText: «{text}»")

                # exit phrases
                if any(text.endswith(p) or text == p for p in exit_phrases):
                    log.info("Завершення за командою користувача.")
                    break

                # parse in NLU
                try:
                    nlu = c.parse(text)       # очікуємо dict: ok/intent/slots/confidence/reply/action
                except Exception as e:
                    log.exception(f"ERR: не вдалося звернутись до NLU: {e}", file=sys.stderr)
                    continue

                if not nlu.get("ok"):
                    log.error(f"ERR: {nlu.get("error")}")
                    continue

                if args.print_intents:
                    log.info(f"intent={nlu['intent']} slots={nlu['slots']} conf={nlu['confidence']}")

                if "action" in nlu:
                    log.info(f"action: {nlu["action"]}")

                if "reply" in nlu:
                    log.info(f"reply: {nlu["reply"]}")

                if args.say_ok:
                    reply = nlu.get("reply")
                    if reply:
                        try:
                            pcm_out = tts.synth(reply)
                            play_pcm_s16le(pcm_out, tts.sample_rate())
                        except Exception as e:
                            log.exception(f"ERR: TTS synth/play failed: {e}", file=sys.stderr)

        except KeyboardInterrupt:
            log.info("\nЗавершення…")
        # Recorder context сам викличе stop()/release()
    return

# entry point
if __name__ == "__main__":
    main()
