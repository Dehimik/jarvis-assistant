from __future__ import annotations
import re
import yaml
from rapidfuzz import fuzz
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterable, Set, Sequence
from .entities import compile_pattern

Rule = Tuple[str, re.Pattern]
BaseEntry = Tuple[str, str]  # (intent_name, base_text)

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def _strip_regex(pat: str) -> str:
    # оголюємо патерн до «словесної бази» для фузі
    s = re.sub(r"\(\?P<[^>]+>[^)]+\)", " ", pat)   # іменовані групи → пробіл
    s = re.sub(r"\\s\+", " ", s)                   # \s+ → пробіл
    s = s.replace("^", " ").replace("$", " ")
    s = re.sub(r"[\\\^\$\|\[\]\(\)\?\*\+\{\}]", " ", s)
    return _norm(s)

def _deanchor(pat: str) -> str:
    # знімаємо лише крайні ^/$ — внутрішні не чіпаємо
    if pat.startswith("^"):
        pat = pat[1:]
    if pat.endswith("$"):
        pat = pat[:-1]
    return pat

def _slots_from_match(m: re.Match) -> Dict[str, str]:
    gd = m.groupdict() or {}
    return {k: v for k, v in gd.items() if v is not None}

def best_levenshtein(text: str, corpus: Iterable[BaseEntry]) -> Tuple[Optional[str], float]:
    """
    Обирає найкращий intent за RapidFuzz серед [(name, base_text), ...].
    Повертає (name_or_None, score 0..100).
    """
    cleaned = _norm(text)
    best_name, best_sc = None, 0.0
    for name, base in corpus:
        if not base:
            continue
        sc = max(
            fuzz.QRatio(cleaned, base),
            fuzz.partial_ratio(cleaned, base),
            fuzz.token_set_ratio(cleaned, base),
        )
        if sc > best_sc:
            best_name, best_sc = name, sc
    return best_name, best_sc

def best_levenshtein_with_action(
    text: str,
    corpus: Iterable[Tuple[str, str, Sequence[str]]],  # (intent, base_text, action_variants)
    action_bonus: int = 8,  # бонус до скору, якщо добре збігся дієслівний тригер
    action_min: int = 55,   # мінімальний скор для урахування бонусу
) -> Tuple[Optional[str], float]:
    """
    Повертає (best_intent, score 0..100) з урахуванням «головного слова» (action).
    score = max(fuzzy(text, base_text)) [+ bonus якщо збігся якийсь action-варіант].
    """
    cleaned = _norm(text)
    best_name, best_score = None, 0.0

    for name, base, actions in corpus:
        if not base and not actions:
            continue

        base_sc = max(
            fuzz.QRatio(cleaned, base) if base else 0,
            fuzz.partial_ratio(cleaned, base) if base else 0,
            fuzz.token_set_ratio(cleaned, base) if base else 0,
        )

        act_sc = 0
        if actions:
            for a in actions:
                sc = max(
                    fuzz.partial_ratio(cleaned, a),
                    fuzz.token_set_ratio(cleaned, a),
                    fuzz.QRatio(cleaned, a),
                )
                if sc > act_sc:
                    act_sc = sc

        total = base_sc + (action_bonus if act_sc >= action_min else 0)

        if total > best_score:
            best_name, best_score = name, total

    # обрізаємо до 100, щоб не «перебивало» нормалізацію
    return best_name, min(best_score, 100.0)

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
        cleaned = _norm(text)
        for name, rx in self._rules:
            m = rx.fullmatch(cleaned)
            if m:
                return name, self._normalize(name, _slots_from_match(m))
        return None

    def partial_candidates(self, text: str) -> List[Tuple[str, Dict[str, str], int, str]]:
        """
        Повертає список кандидатів часткового збігу:
        [(intent_name, slots, match_len, base_text_for_intent), ...]
        Без ранжування — це робитиме верхній рівень.
        """
        cleaned = _norm(text)
        out: List[Tuple[str, Dict[str, str], int, str]] = []
        for name, rx in self._rules:
            pat = _deanchor(rx.pattern)
            try:
                rx_partial = re.compile(pat, rx.flags)
            except re.error:
                continue
            m = rx_partial.search(cleaned)
            if not m:
                continue
            base = _strip_regex(rx.pattern)
            out.append((name, self._normalize(name, _slots_from_match(m)), len(m.group(0)), base))
        return out

        # ==== База для фузі (для всіх або підмножини інтентів) ====

    def action_variants(self, intent: str, slot_name: str = "action") -> List[str]:
        """
        Повертає варіанти тригерів дії (наприклад 'відкрий','запусти') для інтенту.
        Бере їх зі словника синонімів слота `action`.
        """
        m = self._canon_map.get(intent, {})
        vmap = m.get(slot_name, {})  # variant_lower -> canonical
        return list(vmap.keys())

    def base_corpus(self, only_names: Optional[Set[str]] = None) -> List[Tuple[str, str]]:
        corpus: List[Tuple[str, str]] = []
        for name, rx in self._rules:
            if only_names and name not in only_names:
                continue
            base = _strip_regex(rx.pattern)
            if base:
                corpus.append((name, base))
        return corpus

    def base_corpus_with_actions(
            self, only_names: Optional[Set[str]] = None, slot_name: str = "action"
    ) -> List[Tuple[str, str, List[str]]]:
        """
        Як base_corpus, але додає список варіантів дієслівних тригерів для кожного інтенту.
        """
        out: List[Tuple[str, str, List[str]]] = []
        for name, rx in self._rules:
            if only_names and name not in only_names:
                continue
            base = _strip_regex(rx.pattern)
            actions = self.action_variants(name, slot_name=slot_name)
            out.append((name, base, actions))
        return out

    def fuzzy_slots(self, intent: str, text: str, min_score: int = 60) -> Dict[str, str]:
        """
        Підбирає значення слотів фузі-порівнянням сказаного тексту
        зі словником синонімів для даного intent.
        Повертає {slot: canonical_value}.
        """
        if intent not in self._canon_map:
            return {}

        cleaned = _norm(text)
        result: Dict[str, str] = {}

        if intent not in self._canon_map:
            return {}
        cleaned = _norm(text)
        result: Dict[str, str] = {}
        for slot, variants_map in self._canon_map[intent].items():
            best_can, best_sc = None, 0.0
            for variant_lower, canonical in variants_map.items():
                sc = max(
                    fuzz.partial_ratio(cleaned, variant_lower),
                    fuzz.token_set_ratio(cleaned, variant_lower),
                    fuzz.QRatio(cleaned, variant_lower),
                )
                if sc > best_sc:
                    best_sc, best_can = sc, canonical
            if best_can is not None and best_sc >= min_score:
                result[slot] = best_can
        return result

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
