from __future__ import annotations
import argparse
import uvicorn
from assistant.bus.client import BusClient
from assistant.telemetry.log import setup_logger

log = setup_logger(app_name="jarvis", level="ERROR", env="dev", serialize=False)

def run_daemon(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run("assistant.bus.server:app", host=host, port=port, reload=False, workers=1)

def run_cli():
    parser = argparse.ArgumentParser(prog="va-cli", description="Voice Assistant CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_parse = sub.add_parser("parse", help="Parse text via NLU (and execute via plugins)")
    p_parse.add_argument("text", type=str, help="Text to parse")

    sub.add_parser("reload-nlu", help="Reload YAML intents")

    p_host = parser.add_argument_group("server")
    p_host.add_argument("--url", default="http://127.0.0.1:8000", help="Bus base URL")

    args = parser.parse_args()
    c = BusClient(base_url=args.url)

    if args.cmd == "parse":
        res = c.parse(args.text)
        if not res.get("ok"):
            log.error(res)
            print("ERR:", res.get("error"))
            raise SystemExit(1)
        print(f"intent={res['intent']} slots={res['slots']} conf={res['confidence']}")
        if "action" in res:
            print("action:", res["action"])
    elif args.cmd == "reload-nlu":
        res = c.reload_nlu()
        print("ok" if res.get("ok") else res)
