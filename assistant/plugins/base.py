from abc import ABC, abstractmethod
from typing import Any, Dict

class Plugin(ABC):
    """Базовий інтерфейс для всіх плагінів асистента.
    Кожен плагін повинен успадковувати цей клас і реалізувати три методи:
      • metadata() — повертає інформацію про плагін (name, version, author...)
      • capabilities() — описує, які інтенти та дозволи підтримуються
      • handle(intent) — основний метод виконання дії за інтенцією
    """

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Повертає метадані плагіна."""
        ...

    @abstractmethod
    def capabilities(self) -> Dict[str, Any]:
        """Повертає структуру з описом інтенцій і дозволів плагіна."""
        ...

    @abstractmethod
    async def handle(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Виконує дію для переданої інтенції.
        Повертає словник результату: {'ok': bool, 'data'| 'error': str}.
        """
        ...