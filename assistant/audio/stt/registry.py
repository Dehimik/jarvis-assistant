from typing import Callable, Dict
from .base import STTPlugin
import importlib.util, sys
from pathlib import Path

_registry: Dict[str, Callable[..., STTPlugin]] = {}

def register(name: str):
    def wrap(ctor: Callable[..., STTPlugin]):
        _registry[name] = ctor
        return ctor
    return wrap

def create(name: str, **kwargs) -> STTPlugin:
    if name not in _registry:
        raise ValueError(f"Unknown STT engine: {name}. Available: {list(_registry)}")
    return _registry[name](**kwargs)

def discover(plugins_dir: str | Path):
    """Імпортує всі .py у plugins.d/stt, щоб вони зареєструвались."""
    p = Path(plugins_dir)
    if not p.is_dir(): return
    for file in p.glob("*.py"):
        mod_name = f"stt_{file.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, file)
        if not spec or not spec.loader: continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)

def list_registered() -> list[str]:
    return list(_registry.keys())