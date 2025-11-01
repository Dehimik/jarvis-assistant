from abc import ABC, abstractmethod
from typing import Iterable, Optional, Dict, Any

class TTSPlugin(ABC):
    @abstractmethod
    def sample_rate(self) -> int: ...
    @abstractmethod
    def synth(self, text: str) -> bytes: ...
    def stream(self, text: str) -> Iterable[bytes]:
        yield self.synth(text)
    def list_voices(self) -> list[Dict[str, Any]]: return []
    def set_voice(self, voice_id: str) -> None: ...
