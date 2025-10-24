from ..base import Plugin
import subprocess, shutil, re, os
from pathlib import Path
import psutil
from typing import List, Optional, Tuple, Dict, Any

# helpers for Launcher
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

# helpers for Closer
def _norm(s: str) -> str:
    return (s or "").strip()

def _proc_patterns_for(app: str) -> List[str]:
    """Мапа канонічних назв у типові процеси/рядки cmdline."""
    canon = app.strip().lower()

    table = {
        "telegram": [r"^telegram-desktop$", r"telegram"],
        "chromium": [r"^chromium(-browser)?$", r"chrome", r"chromium"],
        "obsidian": [r"^obsidian$", r"obsidian"],
        "blender": [r"^blender(\.exe)?$", r"blender"],
        # додай свої
    }
    # якщо канонічне значення виглядає як шлях або exec — теж спробуємо ним матчити
    pats = table.get(canon, [])
    pats.append(re.escape(canon))
    return pats

def _terminate_gently(proc: psutil.Process, timeout: float = 2.0) -> str:
    """Повертає 'terminated' | 'killed' | 'alive'."""
    try:
        proc.terminate()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "terminated"
    try:
        proc.wait(timeout=timeout)
        return "terminated"
    except (psutil.TimeoutExpired, psutil.NoSuchProcess):
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "terminated"
        try:
            proc.wait(timeout=timeout)
            return "killed"
        except (psutil.TimeoutExpired, psutil.NoSuchProcess):
            return "alive"

def _xdotool_close(app: str) -> bool:
    """Закриття вікон через xdotool/wmctrl (якщо встановлені)."""
    try:
        if shutil.which("xdotool"):
            # закриємо всі вікна, в заголовку яких є 'app'
            subprocess.run(
                ["xdotool", "search", "--name", app, "windowclose"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
            )
            return True
    except Exception:
        pass
    try:
        if shutil.which("wmctrl"):
            out = subprocess.check_output(["wmctrl", "-l"], text=True)
            hit = False
            for line in out.splitlines():
                if app.lower() in line.lower():
                    wid = line.split()[0]
                    subprocess.run(["wmctrl", "-ic", wid], check=False)
                    hit = True
            return hit
    except Exception:
        pass
    return False

class AppClosePlugin(Plugin):
    def metadata(self): return {"name": "closer", "version": "1.0.0"}

    def capabilities(self):
        return {"intents": ["app.close"], "permissions": ["apps.close"]}

    async def handle(self, intent: Dict[str, Any]):
        """Очікуємо такий самий формат, як у LauncherPlugin."""
        name = intent.get("name")
        slots = intent.get("slots", {}) or {}
        app_value = slots.get("app") or slots.get("url")  # про всяк випадок
        if not app_value:
            return {"ok": False, "error": "missing_value", "intent": name}

        app_raw = _norm(app_value)
        app = app_raw.lower()
        patterns = _proc_patterns_for(app_raw)

        killed, terminated, alive, scanned = [], [], [], 0
        matched_pids = []

        # 1) знаходимо процеси по name/cmdline
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                scanned += 1
                pname = p.info.get("name") or ""
                pcmd = " ".join(p.info.get("cmdline") or [])
                if any(re.search(pt, pname, re.IGNORECASE) or re.search(pt, pcmd, re.IGNORECASE) for pt in patterns):
                    matched_pids.append(p.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 2) гасимо знайдене
        for pid in matched_pids:
            try:
                proc = psutil.Process(pid)
                res = _terminate_gently(proc)
                if res == "terminated":
                    terminated.append(pid)
                elif res == "killed":
                    killed.append(pid)
                else:
                    alive.append(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                terminated.append(pid)

        # 3) якщо нічого не закрили — пробуємо закрити вікна
        used_x = False
        if not (terminated or killed):
            used_x = _xdotool_close(app)

        ok = bool(terminated or killed or used_x)
        return {
            "ok": ok,
            "intent": name,
            "value": app_raw,
            "matched_pids": matched_pids,
            "terminated": terminated,
            "killed": killed,
            "still_alive": alive,
            "used_window_close": used_x,
            "scanned": scanned,
        }