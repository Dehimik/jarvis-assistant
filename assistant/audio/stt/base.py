from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Sequence

class STTPlugin(ABC):
    @abstractmethod
    def sample_rate(self) -> int: ...
    @abstractmethod
    def accept(self, pcm: Sequence[int]) -> Optional[Dict[str, Any]]: ...
    def partial(self) -> Optional[Dict[str, Any]]:
        return None
