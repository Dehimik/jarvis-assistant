from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Any, Dict
from loguru import logger as _logger


# ---------- Публічний API -----------------------------------------------------

def setup_logger(
    app_name: str = "jarvis",
    level: str = "INFO",
    log_dir: str = "logs",
    serialize: bool = False,
    env: Optional[str] = None,
    intercept_std_logging: bool = True,
) -> "_BoundLogger":
    """
    Ініціалізує loguru:
    - Якщо JARVIS_CAPTURE_STDOUT=1 -> лише stdout (щоб батько міг читати і сам писати файл)
    - Інакше -> консоль + файл(и)
    """
    env = env or os.getenv("APP_ENV", "dev")
    capture_stdout = os.getenv("JARVIS_CAPTURE_STDOUT") is not None and os.getenv("JARVIS_CAPTURE_STDOUT") != "0"

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    _logger.remove()  # прибираємо дефолтний sink

    # Формат для консолі
    console_fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
        "| <level>{level: <8}</level> "
        "| <cyan>{process}</cyan>:<cyan>{thread}</cyan> "
        "| <magenta>{module}</magenta>:<magenta>{function}</magenta>:<magenta>{line}</magenta> "
        "- <level>{message}</level>"
        "{exception}"
    )

    # Якщо процес запущено для capture stdout — пишемо лише в stdout (не додаємо файли)
   # if capture_stdout:
        # Лог у stdout (щоб батько читав з PIPE)
    _logger.add(
        sys.stdout,
        level=level,
        colorize=False,  # якщо хочеш кольори у дочірньому процесі — можна True, але краще False для маш. читання
        backtrace=False,
        diagnose=False,
        format=console_fmt,
        enqueue=True,
    )
    """     else:
        # 1) Консоль (stderr для dev, але можна і stdout)
        _logger.add(
            sys.stderr,
            level=level,
            colorize=False,
            backtrace=(env == "dev"),
            diagnose=(env == "dev"),
            format=console_fmt,
            enqueue=True,
        )

        # 2) Основний файл (щоденна ротація)
        _logger.add(
            log_path / f"{app_name}_{{time:YYYY-MM-DD}}.log",
            level=level,
            rotation="00:00",
            retention="7 days",
            compression="zip",
            enqueue=True,
            serialize=False,  # текстовий лог
        )

        # 3) Помилки в окремий файл
        _logger.add(
            log_path / f"{app_name}_errors.log",
            level="ERROR",
            rotation="10 MB",
            retention="14 days",
            compression="zip",
            enqueue=True,
            serialize=False,
        )

        # 4) (опційно) JSON-лог (зручно парсити системами збору логів)
        if serialize:
            _logger.add(
                log_path / f"{app_name}_structured_{{time:YYYY-MM-DD}}.jsonl",
                level=level,
                rotation="00:00",
                retention="7 days",
                enqueue=True,
                serialize=True,
            )

    # Перехоплюємо стандартний logging → loguru (за потреби)
    if intercept_std_logging:
        _intercept_std_logging()
```"""
    # Базовий контекст
    bound = _logger.bind(app=app_name, env=env)
    return _BoundLogger(bound)


def get_logger(**context: Any) -> "_BoundLogger":
    """Отримати логер з додатковим контекстом."""
    return _BoundLogger(_logger.bind(**context))


def log_exceptions(level: str = "ERROR"):
    """
    Декоратор: логувати невиловлені виключення.
    Залишає поведінку оригінальної помилки (перекидає далі).
    """
    def _wrap(func):
        from functools import wraps

        @wraps(func)
        def _inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                _logger.opt(exception=True).log(level, f"Unhandled exception in {func.__name__}")
                raise
        return _inner
    return _wrap


class _BoundLogger:
    """
    Тонка обгортка навколо loguru.Logger для підказок типів та зручностей.
    """
    def __init__(self, bound):
        self._bound = bound

    # Проксі основних методів
    def debug(self, *a, **kw):  self._bound.debug(*a, **kw)
    def info(self, *a, **kw):   self._bound.info(*a, **kw)
    def warning(self, *a, **kw): self._bound.warning(*a, **kw)
    def error(self, *a, **kw):  self._bound.error(*a, **kw)
    def exception(self, *a, **kw): self._bound.exception(*a, **kw)
    def critical(self, *a, **kw): self._bound.critical(*a, **kw)

    def bind(self, **context: Any) -> "_BoundLogger":
        return _BoundLogger(self._bound.bind(**context))

    def context(self, **context: Any) -> "_BoundLogger":
        """Alias до bind, для читабельності."""
        return self.bind(**context)

    def log(self, level: str, message: str, **kwargs: Any):
        self._bound.log(level, message, **kwargs)

    def opt(self, *a, **kw):
        """Доступ до loguru .opt() (наприклад, depth, exception=True)."""
        return self._bound.opt(*a, **kw)


# ---------- Внутрішнє: перехоплення std logging -------------------------------

class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Зберігаємо правильну глибину стеку
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[attr-defined]
            depth += 1
        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _intercept_std_logging() -> None:
    # Глобально
    logging.root.handlers = [ _InterceptHandler() ]
    logging.root.setLevel(logging.NOTSET)

    # Найтиповіші логери сторонніх бібліотек
    for name in (
        "uvicorn", "uvicorn.error", "uvicorn.access",
        "gunicorn", "gunicorn.error",
        "asyncio", "sqlalchemy", "httpx", "requests",
    ):
        _replace_handlers(name)


def _replace_handlers(name: str) -> None:
    lg = logging.getLogger(name)
    lg.handlers = [ _InterceptHandler() ]
    lg.propagate = False
    lg.setLevel(logging.NOTSET)
