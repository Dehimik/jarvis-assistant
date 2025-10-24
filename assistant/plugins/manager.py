from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable

from .base import Plugin
from .builtin.launcher import LauncherPlugin, AppClosePlugin

class PluginManager:
    def __init__(self, builtin: Optional[List[Plugin]] = None):
        self.plugins: List[Plugin] = builtin or [LauncherPlugin(), AppClosePlugin()]
        self.intent_index: Dict[str, Plugin] = {}
        self._index_capabilities()

    def _index_capabilities(self):
        for p in self.plugins:
            caps = p.capabilities() or {}
            for intent in caps.get("intents", []):
                self.intent_index[intent] = p

    def get_for_intent(self, intent_name: str) -> Optional[Plugin]:
        return self.intent_index.get(intent_name)

    async def dispatch(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """intent = {'name': str, 'slots': {...}}"""
        p = self.get_for_intent(intent["name"])

        if not p:
            return {"ok": False, "error": "no_plugin_for_intent", "intent": intent["name"]}
        return await p.handle(intent)
