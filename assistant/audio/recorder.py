from pvrecorder import PvRecorder
import contextlib

class Recorder:
    def __init__(self, device_index: int, frame_length: int):
        self.device_index = device_index
        self.frame_length = frame_length
        self._rec = None

    def start(self):
        if self._rec is None:
            self._rec = PvRecorder(device_index = self.device_index, frame_length = self.frame_length)
        self._rec.start()
        return self._rec.selected_device

    def read(self):
        return self._rec.read()

    def stop(self):
        if self._rec:
            self._rec.stop()

    def release(self):
        if self._rec:
            self._rec.delete()
            self._rec = None

    @contextlib.contextmanager
    def recorder_ctx(device_index: int, frame_length: int):
        rec = Recorder(device_index, frame_length)
        try:
            yield rec
        finally:
            rec.stop()
            rec.release()