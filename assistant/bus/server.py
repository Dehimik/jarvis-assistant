from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from assistant.nlu import NLU
from assistant.plugins.manager import PluginManager

MANIFEST_DIRS = [Path("configs") / "plugins.d"]

class ParseIn(BaseModel):
    text: str

app = FastAPI(title="VA Bus")

app.state.nlu = NLU(MANIFEST_DIRS)
app.state.plugins = PluginManager() # тут підключений LauncherPlugin

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

    return {
        "ok": bool(action.get("ok")),
        "intent": res.intent.name,
        "slots": res.intent.slots,
        "confidence": res.confidence,
        "action": action,
    }
