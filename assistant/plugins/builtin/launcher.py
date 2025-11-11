from ..base import Plugin
import subprocess, shutil, re, os
from pathlib import Path
import psutil
from typing import List, Optional, Tuple, Dict, Any

try:
    # Отримуємо абсолютний шлях до *цього* файлу
    CURRENT_FILE_PATH = Path(__file__).resolve()
    # Піднімаємось на 3 рівні: src-tauri -> gui -> jarvis
    PROJECT_ROOT = CURRENT_FILE_PATH.parent.parent.parent
except NameError:
    # Запасний варіант, якщо __file__ не визначено (напр., REPL)
    # Це менш надійно, але краще, ніж нічого.
    print("Warning: __file__ not defined, falling back to CWD.")
    PROJECT_ROOT = Path.cwd().parent.parent # Припускаємо, що CWD це src-tauri

# 2. Визначаємо папку зі скриптами відносно кореня
PROJECT_SCRIPTS_DIR = PROJECT_ROOT / "configs" / "scripts"

print(f"[Launcher] Корінь проекту: {PROJECT_ROOT}")
print(f"[Launcher] Папка скриптів: {PROJECT_SCRIPTS_DIR}")

# helpers for Launcher
def _is_url(s: str) -> bool:
    """
    Перевіряє, чи є рядок URL.
    Ця версія трохи суворіша, щоб не плутати 'file.sh' з 'domain.com'.
    """
    s = s.lower()
    if s.startswith(("http://", "https://", "ftp://", "www.")):
        return True

    if (PROJECT_SCRIPTS_DIR / s).exists():
        return False
    if s.endswith((".sh", ".py")):
        return False

    if "." in s and " " not in s and not s.startswith(("./", "/")):
        common_tlds = [".com", ".org", ".net", ".io", ".dev", ".app", ".page"]
        if any(s.endswith(tld) for tld in common_tlds):
            return True

    return False

def _is_cmd_available(cmd: List[str]) -> bool:
    exe = cmd[0]
    return (os.path.isabs(exe) and Path(exe).exists()) or shutil.which(exe) is not None


def _resolve_exec(app: str) -> Tuple[Optional[List[str]], dict]:
    """Повертає (cmd, debug_info)"""
    dbg = {"strategy": None, "tried": []}
    app = app.strip()

    possible_names = [app]
    if not app.endswith((".sh", ".py")):
        possible_names.append(f"{app}.sh")
        possible_names.append(f"{app}.py")

    dbg["tried"].append(f"project_scripts_dir: {PROJECT_SCRIPTS_DIR}")

    for name in possible_names:
        script_path = PROJECT_SCRIPTS_DIR / name

        if script_path.exists():
            dbg["strategy"] = "project_script"

            if name.endswith(".py"):
                python_exe = shutil.which("python3") or shutil.which("python")
                if python_exe:
                    return [python_exe, str(script_path.resolve())], dbg
                else:
                    dbg["error"] = "python_not_found_for_py_script"
                    return None, dbg

            return [str(script_path.resolve())], dbg

    if _is_url(app):
        dbg["strategy"] = "url"
        if shutil.which("xdg-open"):
            return ["xdg-open", app], dbg
        return None, dbg

    if shutil.which(app):
        dbg["strategy"] = "which"
        return [app], dbg

    common_paths = [
        f"/usr/bin/{app}",
        f"/usr/local/bin/{app}",
        f"{Path.home()}/.local/bin/{app}"
    ]
    for path in common_paths:
        if Path(path).exists():
            dbg["strategy"] = "common_path"
            return [path], dbg

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