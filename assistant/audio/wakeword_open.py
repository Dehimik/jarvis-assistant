# assistant/audio/wakeword_open.py
from pathlib import Path
from openwakeword.model import Model as OWWModel

class WakeWordOpenWakeWord:
    def __init__(
        self,
        model_paths,
        threshold: float = 0.7,
        sample_rate: int = 16000,
        frame_length: int = 512,
        refractory_ms: int = 1500,
        smooth_frames: int = 3,
    ):
        # 1) робимо абсолютні шляхи і перевіряємо наявність файлів
        abs_models = []
        for p in model_paths:
            pp = Path(p)
            if not pp.is_absolute():
                # ← від кореня проєкту: підлаштуй рівень parents під свою структуру
                base = Path(__file__).resolve().parents[2]  # .../assistant
                pp = (base / p).resolve()
            assert pp.is_file(), f"wakeword model not found: {pp}"
            abs_models.append(str(pp))

        self._frame_length = int(frame_length)
        self._thr = float(threshold)
        self._refractory_ms = int(refractory_ms)
        self._last_fire_ms = 0
        self._smooth_frames = max(1, int(smooth_frames))
        self._buf = []

        # 2) ЯВНО кажемо onnx, щоб не ліз у pretrained
        self._oww = OWWModel(
            wakeword_models=abs_models,
            inference_framework="onnx"  # важливо
        )

    @property
    def frame_length(self) -> int:
        return self._frame_length

    def process(self, pcm):
        import time, numpy as np
        x = (np.asarray(pcm, dtype=np.int16).astype(np.float32)) / 32768.0
        probs = self._oww.predict(x) or {}
        p = float(max(probs.values())) if probs else 0.0

        self._buf.append(p)
        if len(self._buf) > self._smooth_frames:
            self._buf.pop(0)
        p_sm = sum(self._buf) / len(self._buf)

        now = int(time.time() * 1000)
        if p_sm >= self._thr and (now - self._last_fire_ms) >= self._refractory_ms:
            self._last_fire_ms = now
            return True
        return False

    def close(self):
        self._oww = None
