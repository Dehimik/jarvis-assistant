# assistant/audio/recorder.py
from __future__ import annotations
from typing import Optional, List
import sounddevice as sd
import numpy as np
import contextlib
import time


class Recorder:
    def __init__(self, device_index: Optional[int] = None, frame_length: int = 1024, sample_rate: int = 16000):
        self.device_index = device_index
        self.frame_length = frame_length
        self.sample_rate = sample_rate
        self._stream: Optional[sd.InputStream] = None
        self._buffer: List[int] = []
        self._running = False

    def _callback(self, indata, frames, time_info, status):
        if status:
            # print(status)  # можна розкоментити для дебага
            pass
        data = (indata[:, 0] if indata.ndim > 1 else indata).astype(np.int16)
        self._buffer.extend(data.tolist())

    def start(self):
        """Запускає запис"""
        if self._running:
            return
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            device=self.device_index,
            channels=1,
            dtype="int16",
            blocksize=self.frame_length,
            callback=self._callback,
        )
        self._stream.start()
        self._running = True
        dev_info = sd.query_devices(self.device_index) if self.device_index is not None else sd.query_devices(None, 'input')
        return dev_info["name"]

    def read(self):
        """Забирає наступний буфер"""
        while len(self._buffer) < self.frame_length:
            time.sleep(0.001)
        chunk = self._buffer[: self.frame_length]
        del self._buffer[: self.frame_length]
        return chunk

    def stop(self):
        if self._stream and self._running:
            self._stream.stop()
            self._running = False

    def release(self):
        if self._stream:
            self._stream.close()
            self._stream = None
        self._buffer.clear()
        self._running = False

@contextlib.contextmanager
def recorder_ctx(device_index: Optional[int] = None, frame_length: int = 1024, sample_rate: int = 16000):
    rec = Recorder(device_index=device_index, frame_length=frame_length, sample_rate=sample_rate)
    try:
        yield rec
    finally:
        rec.stop()
        rec.release()
