from typing import Callable, Dict
from base import TTSPlugin
import importlib.util, sys
from pathlib import Path

_registry: Dict[str, Callable[..., TTSPlugin]] = {}

def register(name: str):
    def wrap(ctor: Callable[..., TTSPlugin]):
        _registry[name] = ctor
        return ctor
    return wrap

def create(name: str, **kwargs) -> TTSPlugin:
    if name not in _registry:
        raise ValueError(f"Unknown TTS engine: {name}. Available: {list(_registry)}")
    return _registry[name](**kwargs)

def discover(plugins_dir: str | Path):
    p = Path(plugins_dir)
    if not p.is_dir(): return
    for file in p.glob("*.py"):
        mod_name = f"plugins_tts_{file.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, file)
        if not spec or not spec.loader: continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
