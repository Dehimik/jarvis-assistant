from __future__ import annotations

import datetime
import os
import subprocess
import sys
import threading
import time
from contextlib import suppress
from enum import Enum
from typing import Optional, List
import json, shutil, yaml, asyncio

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Body, Request, Query
from pydantic import BaseModel
from pathlib import Path

from starlette.middleware.cors import CORSMiddleware

from assistant.nlu import NLU
from assistant.plugins.manager import PluginManager

load_dotenv()

# paths
ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs"
CONFIGS.mkdir(exist_ok=True)

CONFIG_FILE = ROOT / "assistant/config/config.yaml"

PLUGINS_DIR = CONFIGS / "plugins.d"    # маніфести/плагіни
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

INTENTS_DIR = CONFIGS / "intents.d"    # YAML з правилами інтентів
INTENTS_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = ROOT / "assistant/data"
DATA_DIR.mkdir(exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
LOG_FILE = DATA_DIR / "jarvis.log"

MANIFEST_DIRS = [PLUGINS_DIR, INTENTS_DIR]

# STT Runner
# =========================
#      Jarvis (listen) runner via assistant.main
# =========================
class JarvisRunner:
    """
    Стартує/зупиняє assistant.main: listen у окремому процесі.
    В stdout/stderr пишемо у LOG_FILE, щоб було видно у вкладці Logs.
    """
    def __init__(self, log_file: Path, python=sys.executable):
        self._proc: subprocess.Popen | None = None
        self._python = python
        self._log_file = log_file
        self._pump_thr: threading.Thread | None = None
        self._stop_evt = threading.Event()

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(
        self,
        *,
        config: str = CONFIG_FILE,
        plugins_dir: str = PLUGINS_DIR / "voice",
        device: str | int | None = None,
        frame: int = 512,
        print_intents: bool = True,
        say_ok: bool = False,
    ):
        if self.is_running():
            return

        args = [
            self._python, "-u", "-m", "assistant.main",
            "listen",
            "--plugins-dir", plugins_dir,
            "--frame", str(frame),
        ]
        if device is not None and str(device) != "":
            args += ["--device", str(device)]
        if print_intents:
            args.append("--print-intents")
        if say_ok:
            args.append("--say-ok")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["JARVIS_CAPTURE_STDOUT"] = "1"

        # Читаємо stdout у батьківському процесі:
        self._proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # line-buffered reader у батька
            env=env,
            cwd=str(ROOT),
        )

        self._stop_evt.clear()
        self._pump_thr = threading.Thread(target=self._pump_output, name="jarvis-log-pump", daemon=True)
        self._pump_thr.start()

    def _pump_output(self):
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        with self._log_file.open("a", encoding="utf-8", errors="ignore") as f:
            if self._proc and self._proc.stdout:
                for line in self._proc.stdout:
                    f.write(line)
                    f.flush()  # ← критично: зливати одразу
                    if self._stop_evt.is_set():
                        break

    def stop(self, timeout: float = 3.0):
        if not self.is_running():
            return
        self._stop_evt.set()
        with suppress(Exception):
            self._proc.terminate()
            try:
                self._proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=1.0)
        self._proc = None
        if self._pump_thr:
            self._pump_thr.join(timeout=1.0)
            self._pump_thr = None

# models
class IntentFilter(str, Enum):
    """ Валідація параметра 'intent' """
    all = "all"
    app_open = "app.open"
    app_close = "app.close"

class DaysFilter(int, Enum):
    d7 = 7
    d30 = 30
    d90 = 90
    all = 0

class CommandLogSlots(BaseModel):
    app: Optional[str] = None
    # Додайте сюди інші поля, якщо вони є в 'slots'
    class Config:
        orm_mode = False

class CommandLog(BaseModel):
    id: int
    created_at: datetime.datetime
    raw_text: Optional[str] = None
    intent: Optional[str] = None
    slots: Optional[CommandLogSlots] = None # Pydantic розпарсить JSONB
    confidence: Optional[float] = None

    class Config:
        orm_mode = False# Дозволяє Pydantic читати дані з об'єктів БД (напр., asyncpg.Record)
        extra = "ignore"

class ParseIn(BaseModel):
    text: str

class Status(BaseModel):
    online: Optional[bool] = False
    listening: Optional[bool] = False
    speaking: Optional[bool] = False
    version: str = "0.1.0"

class TogglePatch(BaseModel):
    online: Optional[bool] = None
    listening: Optional[bool] = None
    speaking: Optional[bool] = None

class Settings(BaseModel):
    stt_device: Optional[str] = None
    tts_voice: Optional[str] = None
    locale: Optional[str] = "uk-UA"
    openai_key: Optional[str] = None

# app init
app = FastAPI(title="VA Bus")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.state.nlu = NLU(MANIFEST_DIRS)
app.state.plugins = PluginManager() # тут підключений LauncherPlugin
app.state.status = Status()
app.state.jarvis = JarvisRunner(LOG_FILE)


# helpers
def read_settings() -> Settings:
    if SETTINGS_FILE.exists():
        try:
            return Settings(**json.loads(SETTINGS_FILE.read_text()))
        except Exception:
            pass
    return Settings()

def write_settings(s: Settings) -> Settings:
    SETTINGS_FILE.write_text(json.dumps(s.dict(), ensure_ascii=False, indent=2))
    return s

def safe_name(fname: str):
    if ".." in fname:
        raise HTTPException(400, "Invalid path")
    return fname.strip("/")

class NewFileRequest(BaseModel):
    name: str

# system / nlu
@app.on_event("startup")
async def startup():
    # Завантажте DATABASE_URL з .env або конфігурації
    dsn = os.environ.get("JARVIS_DB_DSN")

    # --- FIX: asyncpg не розуміє діалект '+psycopg2' ---
    if dsn and dsn.startswith("postgresql+psycopg2://"):
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://", 1)

    if not dsn:
        print("[ERROR] DATABASE_URL is not set. Database will not be available.")
        app.state.db = None
    else:
        try:
            app.state.db = await asyncpg.create_pool(
                dsn=dsn,
                min_size=1,
                max_size=10
            )
            print("[INFO] Database pool created successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to create database pool: {e!r}")
            app.state.db = None


@app.on_event("shutdown")
async def shutdown():
    if app.state.db:
        await app.state.db.close()
        print("[INFO] Database pool closed.")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/reload-nlu")
def reload_nlu():
    app.state.nlu.reload()
    return {"ok": True}

@app.post("/intents/parse")
async def intents_parse(body: ParseIn):
    res = app.state.nlu.parse(body.text)
    if not res.ok or not res.intent:
        return {"ok": False, "error": res.error}

    intent_dict = {"name": res.intent.name, "slots": res.intent.slots}
    action = await app.state.plugins.dispatch(intent_dict)  # ← виконуємо дію

    reply_text = app.state.nlu.get_reply(res, action)

    return {
        "ok": bool(action.get("ok")),
        "intent": res.intent.name,
        "slots": res.intent.slots,
        "confidence": res.confidence,
        "action": action,
        "reply": reply_text,
    }

# status
@app.get("/api/status", response_model=TogglePatch)
def get_status():
    return app.state.status

from pydantic import BaseModel
from typing import Optional
from fastapi import HTTPException

class TogglePatch(BaseModel):
    online: Optional[bool] = None
    listening: Optional[bool] = None
    speaking: Optional[bool] = None

@app.post("/api/status/toggle", response_model=Status)
def toggle_status(patch: TogglePatch):
    st: Status = app.state.status
    print(f"[TOGGLE] patch={patch.dict()} BEFORE={st.dict()}")

    if patch.online is not None:
        st.online = bool(patch.online)
        if not st.online:
            st.listening = False
            st.speaking = False
            app.state.jarvis.stop()

    if patch.listening is not None:
        if patch.listening:
            app.state.jarvis.stop()
            st.speaking = False

            try:
                s = read_settings().dict()
                app.state.jarvis.start(
                    plugins_dir="configs/plugins.d/voice",
                    device=s.get("stt_device"),
                    frame=512,
                    print_intents=True,
                    say_ok=False,
                )
                st.online = True
                st.listening = True
            except Exception as e:
                st.listening = False
                st.speaking = False
                print(f"[TOGGLE] start listening failed: {e!r}")
                raise HTTPException(status_code=500, detail=f"failed to start listening: {e}")
        else:
            app.state.jarvis.stop()
            st.listening = False
            st.speaking = False

    if patch.speaking is not None:
        if patch.speaking:
            app.state.jarvis.stop()
            st.listening = False

            try:
                s = read_settings().dict()
                app.state.jarvis.start(
                    plugins_dir="configs/plugins.d/voice",
                    device=s.get("stt_device"),
                    frame=512,
                    print_intents=True,
                    say_ok=True,
                )
                st.online = True
                st.speaking = True
            except Exception as e:
                st.speaking = False
                st.listening = False
                print(f"[TOGGLE] start speaking failed: {e!r}")
                raise HTTPException(status_code=500, detail=f"failed to start speaking: {e}")
        else:
            app.state.jarvis.stop()
            st.speaking = False
            st.listening = False

    print(f"[TOGGLE] AFTER={st.dict()}")
    return st


# settings
@app.get("/api/settings", response_model=Settings)
def api_get_settings():
    return read_settings()

@app.post("/api/settings", response_model=Settings)
def api_update_settings(patch: dict):
    s = read_settings()
    for k, v in patch.items():
        if hasattr(s, k):
            setattr(s, k, v)
    return write_settings(s)

# logs
@app.get("/api/logs")
def get_logs(tail: int = 1000):
    if not LOG_FILE.exists():
        return {"lines": []}
    lines = LOG_FILE.read_text(errors="ignore").splitlines()[-tail:]
    return {"lines": lines}

@app.get("/api/log-path")
def get_log_path():
    # LOG_FILE - це об'єкт Path, .resolve() гарантує абсолютний шлях
    return {"path": str(LOG_FILE.resolve())}

@app.websocket("/api/logs/stream")
async def logs_stream(ws: WebSocket):
    try:
        await ws.accept()
        # (не обов'язково, але корисно) перевіряти Origin, якщо хочеш:
        # origin = ws.headers.get("origin")

        # дати стартовий хвіст (щоб щось показалось одразу)
        tail = 500
        if LOG_FILE.exists():
            try:
                lines = LOG_FILE.read_text(errors="ignore").splitlines()[-tail:]
                if lines:
                    await ws.send_text("\n".join(lines))
            except Exception as e:
                # просто логнемо в консоль
                print(f"[WS] failed to send initial tail: {e!r}")

        # початковий офсет
        last_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

        # цикл: tail -f + keep-alive пінги
        ping_every = 20  # сек
        t_last_ping = asyncio.get_event_loop().time()

        while True:
            await asyncio.sleep(0.5)

            # keep-alive, щоб проксі/в'ю не рубали з’єднання
            now = asyncio.get_event_loop().time()
            if now - t_last_ping > ping_every:
                try:
                    await ws.send_text("")  # дрібний ping (або ws.send_bytes(b''))
                except Exception as e:
                    print(f"[WS] ping failed: {e!r}")
                    break
                t_last_ping = now

            if not LOG_FILE.exists():
                continue

            size = LOG_FILE.stat().st_size
            if size > last_size:
                try:
                    with LOG_FILE.open("r", errors="ignore") as f:
                        f.seek(last_size)
                        chunk = f.read()
                    last_size = size
                    if chunk:
                        for line in chunk.splitlines():
                            await ws.send_text(line)
                except Exception as e:
                    print(f"[WS] read/send failed: {e!r}")
                    break

    except WebSocketDisconnect:
        # клієнт закрився — ок
        return
    except Exception as e:
        # якщо звалилось до accept — браузер бачить “closed before established”
        print(f"[WS] handshake/handler error: {e!r}")
    finally:
        # нічого, просто вийдемо
        pass


# plugins
@app.get("/api/plugins")
def list_plugins():
    items = []
    for p in sorted(PLUGINS_DIR.glob("*")):
        if p.is_dir():
            items.append({"name": p.name + "/", "dir": True})
        else:
            items.append({"name": p.name, "size": p.stat().st_size})
    return {"plugins": items}

@app.post("/api/plugins/upload")
def upload_plugin(name: str, file: UploadFile = File(...)):
    nm = safe_name(name)
    dst = PLUGINS_DIR / nm
    with dst.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    # після оновлення маніфестів — можна перезібрати NLU
    app.state.nlu.reload()
    return {"ok": True, "name": nm}

@app.delete("/api/plugins/{name}")
def delete_plugin(name: str):
    nm = safe_name(name)
    path = PLUGINS_DIR / nm
    if not path.exists():
        raise HTTPException(404, "not found")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    app.state.nlu.reload()
    return {"ok": True}

# intents
@app.post("/api/intents/new")
def new_intent_file(request: NewFileRequest):
    """
    Очікує JSON тіло: {"name": "path/to/file"}
    """
    nm = safe_name(request.name)

    if not (nm.endswith(".yml") or nm.endswith(".yaml")):
        nm += ".yaml"

    path = INTENTS_DIR / nm

    if path.exists():
       raise HTTPException(409, "exists")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(500, f"Could not create directory: {e}")

    default_template = {}

    path.write_text(yaml.safe_dump(default_template,
                                   allow_unicode=True, sort_keys=False), encoding="utf-8")

    app.state.nlu.reload()

    return {"ok": True, "name": nm}

@app.post("/api/intents/{fname:path}")
def save_intent_file(fname: str, content: str = Body(..., media_type="text/plain")):
    """
    Отримує простий текст (text/plain) з тіла запиту.
    """
    nm = safe_name(fname)

    path = INTENTS_DIR / nm

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(500, f"Could not create directory for saving: {e}")

    path.write_text(content, encoding="utf-8")

    app.state.nlu.reload()
    return {"ok": True, "name": nm}

@app.get("/api/intents/{fname:path}")
def get_intent_file(fname: str):
    nm = safe_name(fname)
    path = INTENTS_DIR / nm
    if not path.exists():
        raise HTTPException(404, "not found")
    return {"name": nm, "text": path.read_text(encoding="utf-8")}


@app.delete("/api/intents/{fname:path}")
def delete_intent_file(fname: str):
    nm = safe_name(fname)
    path = INTENTS_DIR / nm
    if not path.exists():
        raise HTTPException(404, "not found")
    path.unlink()
    app.state.nlu.reload()
    return {"ok": True}

@app.get("/api/intents")
def list_intents():
    items = []
    # Використовуємо .rglob() для рекурсивного пошуку в підпапках
    yml_files = sorted(INTENTS_DIR.rglob("*.yml"))
    yaml_files = sorted(INTENTS_DIR.rglob("*.yaml"))

    all_files = yml_files + yaml_files
    processed_paths = set()  # Використовуємо set для уникнення дублікатів

    for p in all_files:
        # Отримуємо шлях відносно INTENTS_DIR (напр., "subdir/file.yml")
        # і нормалізуємо слеші для сумісності
        relative_path = str(p.relative_to(INTENTS_DIR)).replace("\\", "/")

        if relative_path not in processed_paths:
            items.append({"name": relative_path})
            processed_paths.add(relative_path)

    # Сортуємо фінальний список за іменем
    items.sort(key=lambda x: x['name'])

    return {"files": items}

#database
@app.get("/api/statistics", response_model=List[CommandLog])
async def get_statistics(
        request: Request,  # Потрібен для доступу до app.state.db
        intent: IntentFilter = Query(IntentFilter.all, description="Filter by intent type"),
        days: DaysFilter = Query(DaysFilter.d30, description="Filter by time period")
):
    """
    Надає історію команд для сторінки аналітики.
    """

    # 1. Отримуємо пул з'єднань, який ми (припускаємо) створили при старті
    db_pool = request.app.state.db
    if not db_pool:
        raise HTTPException(
            status_code=500,
            detail="Database connection is not configured on the server (app.state.db is missing)."
        )

    # 2. Базовий SQL-запит (використовуємо $1, $2 для безпечних параметрів)
    query = """
            SELECT id, created_at, raw_text, intent, slots, confidence
            FROM command_history \
            """

    conditions = []
    params = []  # Список для параметрів запиту

    # 3. Додаємо NOT NULL фільтри за вашим запитом
    conditions.append("raw_text IS NOT NULL")
    conditions.append("intent IS NOT NULL")
    conditions.append("slots IS NOT NULL")
    conditions.append("confidence IS NOT NULL")

    # 4. Динамічно додаємо фільтри

    # Фільтр за датою
    if days.value > 0:
        params.append(datetime.timedelta(days=days.value))
        # Використовуємо 'now() - $1::interval'
        conditions.append(f"created_at >= (now() - ${len(params)}::interval)")

    # Фільтр за інтентом
    if intent.value != "all":
        params.append(intent.value)
        conditions.append(f"intent = ${len(params)}")

    # 4. Збираємо запит
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Завжди сортуємо, щоб показувати останні
    query += " ORDER BY created_at DESC"
    # Додамо ліміт, щоб не перевантажувати фронтенд
    query += " LIMIT 500"

    try:
        records = await db_pool.fetch(query, *params)  # asyncpg.Record list

        # Варіант A — повертати прості dict'и (найпростіший, рекомендований)
        result: List[dict] = []
        for r in records:
            d = dict(r)  # asyncpg.Record -> dict
            # Якщо slots зберігаються як JSON string, розпарсимо в dict
            slots_value = d.get("slots")
            if isinstance(slots_value, str):
                try:
                    d["slots"] = json.loads(slots_value)
                except Exception:
                    # якщо не JSON — залишаємо як є
                    pass
            result.append(d)

        # (опція) швидке логування першого елементу для діагностики:
        if result:
            print("[DEBUG] /api/statistics first record:", result[0])

        return result

        # Альтернатива B — створити Pydantic-об'єкти на сервері:
        # return [CommandLog(**dict(r)) for r in records]

    except Exception as e:
        print(f"[ERROR] /api/statistics query failed: {e!r}")
        raise HTTPException(status_code=500, detail=f"Database query failed.")