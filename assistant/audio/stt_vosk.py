from pathlib import Path

import vosk, json, struct

def _resolve_vosk_model_dir(base: str | Path) -> Path:
    p = Path(base).resolve()
    # якщо прямо тут вже є потрібні підпапки — ок
    if (p / "am").is_dir() and (p / "conf").is_dir():
        return p
    # інакше спробуємо знайти єдину підпапку, де вони є
    candidates = [d for d in p.iterdir() if d.is_dir()]
    for d in candidates:
        if (d / "am").is_dir() and (d / "conf").is_dir():
            return d
    raise FileNotFoundError(
        f"Vosk model dir not found under {p}. "
        f"Expecting subfolders like 'am/' and 'conf/'. "
        f"Found: {[c.name for c in candidates]}"
    )

class VoskSTT:
    def __init__(self, model_path: str | Path = "assistant/audio/models/vosk-model-uk-v3", sample_rate: int = 16000):
        model_dir = _resolve_vosk_model_dir(model_path)
        self.model = vosk.Model(str(model_dir))
        self.sr = sample_rate
        self.rec = vosk.KaldiRecognizer(self.model, self.sr)

    def accept(self, pcm) -> dict | None:
        sp = struct.pack("h" * len(pcm), *pcm)
        if self.rec.AcceptWaveform(sp):
            res = json.loads(self.rec.Result())
            return res
        return None

    def partial(self) -> dict:
        return json.loads(self.rec.PartialResult())