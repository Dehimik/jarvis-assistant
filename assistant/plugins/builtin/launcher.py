from ..base import Plugin
import subprocess, shutil, re, os
from pathlib import Path
from typing import List, Optional, Tuple

def _is_url(s: str) -> bool:
    return bool(re.match(r"^(https?://|www\.)", s)) or ("." in s and " " not in s)

def _is_cmd_available(cmd: List[str]) -> bool:
    exe = cmd[0]
    return (os.path.isabs(exe) and Path(exe).exists()) or shutil.which(exe) is not None

def _resolve_exec(app: str) -> Tuple[Optional[List[str]], dict]:
    """Повертає (cmd, debug_info)"""
    dbg = {"strategy": None, "tried": []}
    app = app.strip()

    # URL → xdg-open
    if _is_url(app):
        dbg["strategy"] = "url"
        if shutil.which("xdg-open"):
            return ["xdg-open", app], dbg
        return None, dbg

    if shutil.which(app):
        dbg["strategy"] = "which"
        return [app], dbg

    return None, dbg

class LauncherPlugin(Plugin):
    def metadata(self): return {"name": "launcher", "version": "1.0.0"}

    def capabilities(self):
        return {"intents": ["app.open", "url.open"], "permissions": ["apps.launch"]}

    async def handle(self, intent):
        name = intent["name"]
        slots = intent.get("slots", {})
        value = slots.get("url") if name == "url.open" else slots.get("app")
        if not value:
            return {"ok": False, "error": "missing_value"}

        cmd, dbg = _resolve_exec(value)
        if not cmd:
            return {"ok": False, "error": "app_not_found", "value": value, "debug": dbg}

        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "launched": cmd}
        except Exception as e:
            return {"ok": False, "error": "exec_failed", "details": str(e), "cmd": cmd, "debug": dbg}