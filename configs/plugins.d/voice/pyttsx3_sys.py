from __future__ import annotations
from typing import Iterable, Optional, Dict, Any

from assistant.audio.tts.base import TTSPlugin
from assistant.audio.tts.registry import register

import pyttsx3
import wave
import tempfile
import os
import numpy as np

@register("pyttsx3")
class Pyttsx3Plugin(TTSPlugin):
    # options from yaml config
    def __init__(self, rate: Optional[int] = None, voice_substr: Optional[str] = None):
        self._engine = pyttsx3.init()
        # Rate options (якщо підтримує бекенд)
        if rate is not None:
            try:
                self._engine.setProperty("rate", int(rate))
            except Exception:
                pass

        # Pick voice
        if voice_substr:
            v = self._pick_voice(voice_substr)
            if v:
                try:
                    self._engine.setProperty("voice", v.id)
                except Exception:
                    pass

        self._sr = None  # визначимо при першому synth()

    # ====== API TTSPlugin ======

    def sample_rate(self) -> int:
        # Якщо ще не синтезували — приймемо дефолт; але краще дочекатися synth(), який
        # виставить self._sr з фактичного WAV.
        return int(self._sr or 22050)

    def synth(self, text: str) -> bytes:
        # generate wav file and convert it into bytes
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            self._engine.save_to_file(text, tmp_path)
            self._engine.runAndWait()

            pcm, sr = self._read_wav_as_s16le_mono(tmp_path)
            self._sr = sr
            return pcm
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def stream(self, text: str) -> Iterable[bytes]:
        yield self.synth(text)

    def list_voices(self) -> list[Dict[str, Any]]:
        out = []
        try:
            for v in self._engine.getProperty("voices") or []:
                out.append({
                    "id": getattr(v, "id", ""),
                    "name": getattr(v, "name", ""),
                    "languages": getattr(v, "languages", []),
                    "gender": getattr(v, "gender", None),
                    "age": getattr(v, "age", None),
                })
        except Exception:
            pass
        return out

    def set_voice(self, voice_id: str) -> None:
        try:
            self._engine.setProperty("voice", voice_id)
        except Exception:
            pass

    # ====== helpers ======

    def _pick_voice(self, substr: str):
        s = substr.lower()
        try:
            for v in self._engine.getProperty("voices") or []:
                vid = (getattr(v, "id", "") or "").lower()
                vname = (getattr(v, "name", "") or "").lower()
                if s in vid or s in vname:
                    return v
        except Exception:
            return None
        return None

    @staticmethod
    def _read_wav_as_s16le_mono(path: str) -> tuple[bytes, int]:
        with wave.open(path, "rb") as w:
            nch = w.getnchannels()
            sw = w.getsampwidth()
            sr = w.getframerate()
            n = w.getnframes()
            raw = w.readframes(n)

        # convert to numpy
        if sw == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.int32)  # в int32 для безпечної обробки
        elif sw == 1:
            # 8-bit unsigned -> center into 128 -> into int16
            u8 = np.frombuffer(raw, dtype=np.uint8).astype(np.int32)
            data = (u8 - 128) * 256
        elif sw == 4:
            i32 = np.frombuffer(raw, dtype=np.int32).astype(np.int32)
            # normalize tо int16 diapazon
            data = (i32 // 2048)  # ~ scaling 32->16 біт
        else:
            # unknown format — try in int16
            data = np.frombuffer(raw, dtype=np.int16).astype(np.int32)

        # if stereo — try in mono (average)
        if nch > 1:
            data = data.reshape(-1, nch).mean(axis=1)

        # limit diapazon and return in int16
        data = np.clip(data, -32768, 32767).astype(np.int16)

        return data.tobytes(), sr
