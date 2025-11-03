from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
from .engine import Grammar, load_grammar_from_dirs, best_levenshtein, best_levenshtein_with_action


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
    def __init__(self, plugin_manifest_dirs: List[Path], threshold: int = 50):
        self.manifest_dirs = plugin_manifest_dirs
        self.grammar: Grammar = load_grammar_from_dirs(plugin_manifest_dirs)
        self.threshold = threshold

    def reload(self) -> None:
        self.grammar = load_grammar_from_dirs(self.manifest_dirs)

    def get_reply(self, result: "IntentResult", action: dict | None = None) -> str:
        """
        Повертає текстову відповідь на базі розпізнаного інтенту та результату виконання плагіна.
        Використай це з TTS: tts.synth(reply).
        """
        # 0) Якщо взагалі нічого не розпізнано
        if not result or not result.ok or not result.intent:
            return "Вибач, я не зрозумів команду."

        intent = result.intent.name
        slots = result.intent.slots or {}
        ok = bool(action.get("ok")) if isinstance(action, dict) else False
        err = (action or {}).get("error") if isinstance(action, dict) else None

        # Шаблони відповідей під популярні інтенти (розширюй коли буде потрібно)
        # Якщо інтент невідомий — падаємо на дефолт.
        if intent == "app.open":
            app = slots.get("app") or "додаток"
            if ok:
                # опційно: якщо launcher повертає назву/шлях — підставляємо
                src = (action or {}).get("src") or ""
                if src:
                    return f"Відкриваю {app} ({src})."
                return f"Відкриваю {app}."
            else:
                reason = err or "сталася помилка під час запуску."
                return f"Не вдалося відкрити {app}: {reason}"

        # Дефолт для інших інтентів
        if ok:
            return "Готово."
        else:
            return f"Не вдалося виконати команду{(': ' + err) if err else '.'}"

    def parse(self, text: str) -> IntentResult:
        """
                Флоу:
                1) exact через короткий match (Grammar.match_exact)
                2) partial-кандидати → best_levenshtein по їх базам
                3) глобальний фузі по всій базі правил як запасний варіант

        # 1) exact
        exact = self.grammar.match(text)
        if exact:
            name, slots = exact
            return IntentResult(ok=True, intent=Intent(name, slots), confidence=1.0)
 """
        partials = self.grammar.partial_candidates(text)
        if partials:
            names = {n for (n, _, __, ___) in partials}
            corpus = self.grammar.base_corpus_with_actions(only_names=names)
            best_name, best_sc = best_levenshtein_with_action(text, corpus)
            if best_name is not None and best_sc >= self.threshold:
                best_slots = max(
                    ((n, s, ml) for (n, s, ml, _) in partials if n == best_name),
                    key=lambda t: t[2],
                )[1]
                # дотягуємо action/інші слоти
                fuzzy = self.grammar.fuzzy_slots(best_name, text, min_score=max(55, self.threshold - 10))
                for k, v in fuzzy.items():
                    if k not in best_slots or not best_slots[k]:
                        best_slots[k] = v
                return IntentResult(
                    ok=True,
                    intent=Intent(best_name, best_slots),
                    confidence=best_sc / 100.0
                )

        # 3) ГЛОБАЛЬНИЙ фузі-фолбек (+екшен бонус)
        corpus_all = self.grammar.base_corpus_with_actions()
        best_name, best_sc = best_levenshtein_with_action(text, corpus_all)
        if best_name is not None and best_sc >= self.threshold:
            fuzzy = self.grammar.fuzzy_slots(best_name, text, min_score=max(55, self.threshold - 10))
            return IntentResult(
                ok=True,
                intent=Intent(best_name, fuzzy),
                confidence=best_sc / 100.0
            )

        return IntentResult(ok=False, intent=None, confidence=0.0, error="no_intent")