from pathlib import Path
from typing import Optional, Dict, Any, Sequence
import json
import struct
import vosk

from assistant.audio.stt.base import STTPlugin
from assistant.audio.stt.registry import register

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ASSISTANT_DIR = REPO / "assistant"

def _resolve_vosk_model_dir(model_path: str) -> Path:
    p = Path(model_path)

    # 1) абсолютний шлях — відразу
    if p.is_absolute():
        if p.exists():
            return p
        raise FileNotFoundError(f"Vosk model path (absolute) not found: {p}")

    # 2) кандидати для відносного шляху
    candidates = [
        Path.cwd() / p,            # поточний робочий каталог (виклик процесу)
        ASSISTANT_DIR / p,         # ../assistant/<model_path>
        REPO / p,             # корінь репо / <model_path>
        HERE / p,                  # поруч із плагіном (configs/...)
    ]

    tried = []
    for c in candidates:
        c = c.resolve()
        tried.append(str(c))
        if c.exists():
            # знайшли — якщо це директорія з моделлю, повертаємо її
            # (можна додатково перевірити наявність файлів 'model.conf' або similar)
            return c

    # якщо не знайшли — кинемо детальну помилку з підказкою
    raise FileNotFoundError(
        "Vosk model not found. Tried these locations:\n  - " + "\n  - ".join(tried) +
        "\nPut your model folder (e.g. vosk-model-uk-v3) in one of them or set model_path to an absolute path."
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
