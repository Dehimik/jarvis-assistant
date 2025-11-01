from pathlib import Path
from typing import Any, Dict
import yaml
from assistant.audio.stt.registry import discover as stt_discover, create as stt_create
from assistant.audio.tts.registry import discover as tts_discover, create as tts_create

class ConfigResolver:
    """
    Завантажує YAML-конфіг, підтягує плагіни з plugins.d і створює інстанси STT/TTS.
    """

    def __init__(self, config_path: str | Path = "config.yaml", plugins_dir: str | Path = "assistant/configs/plugins.d"):
        self.config_path = Path(config_path)
        self.plugins_dir = Path(plugins_dir)
        self.cfg: Dict[str, Any] = {}

    def load(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f) or {}

    def _resolve_stt(self):
        stt_section = self.cfg.get("stt", {})
        name = stt_section.get("plugin")
        options = stt_section.get("options", {})
        if not name:
            raise ValueError("Missing 'stt.plugin' in config.yaml")

        stt_discover(self.plugins_dir / "stt")
        return stt_create(name, **options)

    def _resolve_tts(self):
        tts_section = self.cfg.get("tts", {})
        name = tts_section.get("plugin")
        options = tts_section.get("options", {})
        if not name:
            raise ValueError("Missing 'tts.plugin' in config.yaml")

        tts_discover(self.plugins_dir / "tts")
        return tts_create(name, **options)

    def resolve_all(self):
        """Повертає словник із ініціалізованими плагінами."""
        self.load()
        stt_instance = self._resolve_stt()
        tts_instance = self._resolve_tts()
        return {"stt": stt_instance, "tts": tts_instance}
