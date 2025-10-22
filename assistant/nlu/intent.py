from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from .engine import Grammar, load_grammar_from_dirs

@dataclass
class Intent:
    name: str
    slots: Dict[str, str]

@dataclass
class IntentResult:
    ok: bool
    intent: Optional[Intent]
    confidence: float = 0.0
    error: Optional[str] = None

class NLU:
    def __init__(self, plugin_manifest_dirs: List[Path]):
        self.manifest_dirs = plugin_manifest_dirs
        self.grammar: Grammar = load_grammar_from_dirs(plugin_manifest_dirs)

    def reload(self) -> None:
        self.grammar = load_grammar_from_dirs(self.manifest_dirs)

    def parse(self, text: str) -> IntentResult:
        match = self.grammar.match(text)
        if not match:
            return IntentResult(ok=False, intent=None, confidence=0.0, error="no_intent")
        name, slots = match
        return IntentResult(ok=True, intent=Intent(name=name, slots=slots), confidence=1.0)