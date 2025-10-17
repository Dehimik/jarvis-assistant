import pvporcupine

class WakeWordPorcupine:
    def __init__(self, access_key: str, keyword: str = "jarvis", sensitivity: float = 1.0):
        self._ppn = pvporcupine.create(access_key=access_key, keyword_paths=[keyword])

    @property
    def frame_length(self) -> int:
        return self._ppn.frame_length

    def process(self, pcm: bytes) -> int:
        idx = self._ppn.process(pcm)
        return idx >= 0

    def close(self):
        if self._ppn: self._ppn.delete(); self._ppn = None