from __future__ import annotations
import json
from urllib import request

def _post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

class BusClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base = base_url.rstrip("/")

    def parse(self, text: str) -> dict:
        return _post(f"{self.base}/intents/parse", {"text": text})

    def reload_nlu(self) -> dict:
        return _post(f"{self.base}/reload-nlu", {})