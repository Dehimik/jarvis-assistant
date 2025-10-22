from __future__ import annotations
import re
from typing import Dict

# Базові типи слотів
SLOT_REGEXES: Dict[str, str] = {
    "app_name": r"(?P<{name}>[\w\-\.\s]+)",
    "url":      r"(?P<{name}>(?:https?://)?[\w\.-]+(?:\.[a-z]{2,})(?:/[^\s]*)?)",
    "text":     r"(?P<{name}>.+?)",
}

_SLOT_NAME_RE   = re.compile(r"\{(?P<name>\w+)(?::(?P<type>\w+))?\}")
_INNER_GROUP_RE = re.compile(r"^\(\?P<[^>]+>(.*)\)$")  # витяг "inner" з (?P<name>inner)

def _inner_of_named_group(pattern: str) -> str:
    """Повертає внутрішню частину (?P<name> ... ). Безпечний fallback, якщо формат інший."""
    m = _INNER_GROUP_RE.match(pattern)
    if m:
        return m.group(1)
    try:
        start = pattern.index(">") + 1
        end   = pattern.rindex(")")
        return pattern[start:end]
    except Exception:
        return pattern  # краще залишити як є, ніж ламати дужки

def compile_pattern(template: str, slot_synonyms: Dict[str, Dict[str, list]]) -> re.Pattern:
    def slot_repl(m: re.Match):
        name  = m.group("name")
        stype = m.group("type") or "text"
        base  = SLOT_REGEXES.get(stype, SLOT_REGEXES["text"]).format(name=name)
        inner = _inner_of_named_group(base)

        # альтернативи з урахуванням синонімів
        syns_list = []
        for key, variants in (slot_synonyms.get(name, {}) or {}).items():
            if key and key.strip():
                syns_list.append(re.escape(key))
            for v in variants or []:
                if v and str(v).strip():
                    syns_list.append(re.escape(str(v)))

        if syns_list:
            alt = "|".join(sorted(set(syns_list), key=len, reverse=True))
            return rf"(?P<{name}>(?:{alt})|{inner})"
        return rf"(?P<{name}>{inner})"

    # 1) підставляємо слоти
    pat_regex = _SLOT_NAME_RE.sub(slot_repl, template.strip())
    # 2) НОРМАЛІЗАЦІЯ ПРОБІЛІВ: lambda, щоб \s не трактувався як escape у replacement
    pat_regex = re.sub(r"\s+", lambda _: r"\s+", pat_regex)

    try:
        return re.compile(rf"^\s*{pat_regex}\s*$", re.IGNORECASE)
    except re.error as e:
        # зручне діагностичне повідомлення
        raise re.error(f"Pattern compile failed: {e}. RAW=^{pat_regex}$")
