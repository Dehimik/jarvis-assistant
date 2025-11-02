from pathlib import Path
from typing import Optional, Dict, Any, Sequence
import json
import struct
import vosk

from assistant.audio.stt.base import STTPlugin
from assistant.audio.stt.registry import register

def _resolve_vosk_model_dir(base: str | Path) -> Path:
    # search for model dir
    p = Path(base).resolve()
    if (p / "am").is_dir() and (p / "conf").is_dir():
        return p
    candidates = [d for d in p.iterdir() if d.is_dir()]
    for d in candidates:
        if (d / "am").is_dir() and (d / "conf").is_dir():
            return d
    raise FileNotFoundError(
        f"Vosk model dir not found under {p}. "
        f"Expecting subfolders like 'am/' and 'conf/'. "
        f"Found: {[c.name for c in candidates]}"
    )

@register("vosk_uk_v3")
class VoskUkPlugin(STTPlugin):
    # options from yaml config
    def __init__(self, model_path: str, sample_rate: int = 16000):
        model_dir = _resolve_vosk_model_dir(model_path)
        self._sr = sample_rate
        self._model = vosk.Model(str(model_dir))
        self._rec = vosk.KaldiRecognizer(self._model, self._sr)

    def sample_rate(self) -> int:
        return self._sr

    def accept(self, pcm: Sequence[int]) -> Optional[Dict[str, Any]]:
        # accept one frame int16 and return result or None
        sp = struct.pack("h" * len(pcm), *pcm)  # int16 -> bytes s16le
        if self._rec.AcceptWaveform(sp):
            return json.loads(self._rec.Result())
        return None

    def partial(self) -> Optional[Dict[str, Any]]:
        return json.loads(self._rec.PartialResult())
