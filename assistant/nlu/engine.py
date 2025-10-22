from __future__ import annotations
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .entities import compile_pattern

Rule = Tuple[str, re.Pattern]

class Grammar:
    def __init__(self) -> None:
        self._rules: List[Rule] = []
        # intent -> slot -> variant_lower -> canonical
        self._canon_map: Dict[str, Dict[str, Dict[str, str]]] = {}

    def add_intent(
        self,
        name: str,
        patterns: List[str],
        slot_synonyms: Dict[str, Dict[str, List[str]]]
    ):
        # зберігаємо таблицю нормалізації
        slot_map: Dict[str, Dict[str, str]] = {}
        for slot, syn in (slot_synonyms or {}).items():
            canon_for_slot: Dict[str, str] = {}
            for canonical, variants in (syn or {}).items():
                # сам canonical теж мапимо на себе
                canon_for_slot[str(canonical).lower()] = str(canonical)
                for v in (variants or []):
                    if v and str(v).strip():
                        canon_for_slot[str(v).lower()] = str(canonical)
            if canon_for_slot:
                slot_map[slot] = canon_for_slot

        # компілюємо регекси
        for p in (patterns or []):
            try:
                rx = compile_pattern(p, slot_synonyms)
            except re.error as e:
                raise re.error(f"[NLU] intent='{name}' pattern='{p}' -> {e}")
            self._rules.append((name, rx))

        if slot_map:
            self._canon_map[name] = slot_map

    def _normalize(self, intent: str, slots: Dict[str, str]) -> Dict[str, str]:
        if intent not in self._canon_map:
            return slots
        m = self._canon_map[intent]
        out: Dict[str, str] = {}
        for k, v in slots.items():
            vv = v.strip()
            mm = m.get(k)
            if mm:
                out[k] = mm.get(vv.lower(), vv)  # якщо знайдено синонім → canonical
            else:
                out[k] = vv
        return out

    def match(self, text: str) -> Optional[Tuple[str, Dict[str, str]]]:
        for name, rx in self._rules:
            m = rx.match(text)
            if m:
                slots = {k: v for k, v in m.groupdict().items() if v is not None}
                slots = self._normalize(name, slots)
                return name, slots
        return None


def load_grammar_from_dirs(dirs: List[Path]) -> Grammar:
    g = Grammar()
    for d in dirs:
        if not d.is_dir():
            continue
        for f in d.glob("**/intents.yaml"):
            with f.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for intent, spec in (data.get("intents") or {}).items():
                patterns = spec.get("patterns", [])
                slots = spec.get("slots", {})
                slot_syn = {s: slots.get(s, {}).get("synonyms", {}) for s in slots}
                g.add_intent(intent, patterns, slot_syn)
    return g
