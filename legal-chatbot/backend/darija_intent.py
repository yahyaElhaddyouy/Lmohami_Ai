# -*- coding: utf-8 -*-
"""Offline Moroccan Darija intent detection for the RAG entry point."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data" / "darija_dataset"
INTENTS_PATH = DATA_DIR / "intents.json"
EXAMPLES_PATH = DATA_DIR / "darija_examples.jsonl"

OUT_OF_SCOPE_MESSAGE = (
    "ما لقيتش جواب قانوني كافي فالمصدر المتوفر. "
    "هاد المساعد محدود فمدونة الشغل المغربية."
)

DIRECT_INTENTS = {"greeting", "thanks", "goodbye", "unclear"}
NON_LEGAL_INTENTS = DIRECT_INTENTS | {"out_of_scope"}
INTENT_PRIORITY = {
    "maternity_protection": 100,
    "work_accident_compensation": 95,
    "cnss_non_declaration": 90,
    "abusive_dismissal": 85,
    "dismissal": 50,
    "salary_unpaid": 50,
}
SPECIFIC_INTENT_DEFINITIONS = {
    "maternity_protection": {
        "source_intent": "maternity",
        "normalized_query": "maternité grossesse congé maternité حماية المرأة الحامل الولادة أمومة",
        "keywords": [
            "حامل",
            "الحامل",
            "حمل",
            "ولادة",
            "أمومة",
            "امومة",
            "grossesse",
            "حماية الحامل",
            "بعد الولادة",
        ],
    },
    "work_accident_compensation": {
        "source_intent": "work_accident",
        "normalized_query": "accident du travail حادثة شغل إصابة مهنية تصريح حادث الشغل تعويض",
        "keywords": ["حادث", "حادثة شغل", "تجرح", "تجرحت", "تكسرت", "طحت", "ضرباتني", "machine", "الورشة", "تعويض", "accident"],
    },
    "cnss_non_declaration": {
        "source_intent": "cnss",
        "normalized_query": "CNSS الضمان الاجتماعي التصريح بالأجير الاشتراكات الصندوق الوطني للضمان الاجتماعي",
        "keywords": ["cnss", "ضمان", "تصريح", "مصرحش", "ما مصرحش", "سجلني", "cotisation"],
    },
    "abusive_dismissal": {
        "source_intent": "dismissal",
        "normalized_query": "licenciement abusif فصل تعسفي طرد بلا سبب مسطرة الفصل محضر الاستماع",
        "keywords": ["طرد", "طردوني", "حيدوني", "ما تجيش", "منعوني ندخل", "منعني ندخل", "مخلاونيش ندخل", "badge", "fin de contrat", "بلا سبب", "بدون سبب", "تعسفي", "licenciement abusif"],
    },
}
OUT_OF_SCOPE_HINTS = {
    "طلاق",
    "كراء",
    "حادثه سير",
    "حادثة سير",
    "جنائي",
    "ارث",
    "الارث",
    "إرث",
    "دعوى تجاريه",
    "دعوى تجارية",
    "تجاريه",
    "تجارية",
    "مول الدار",
    "الجار",
    "مخالفة",
    "مخالفه",
    "الطريق",
    "البوليس",
    "الشرطة",
    "جنائي",
    "ميراث",
    "إرث",
    "عقار",
    "الهجرة",
    "كندا",
    "ضريبة",
    "impôts",
    "impots",
    "banque",
    "فيزا",
    "فرنسا",
    "code route",
}
WORK_CONTEXT_HINTS = {
    "خدمة",
    "الخدمة",
    "للخدمة",
    "الشغل",
    "العمل",
    "شركة",
    "الشركة",
    "employeur",
    "salarié",
    "salarie",
    "travail",
}

DIRECT_ANSWERS = {
    "greeting": "سلام، مرحبا بيك. سولني على أي سؤال متعلق بمدونة الشغل المغربية.",
    "thanks": "العفو. إلا بغيتي توضيح آخر فمدونة الشغل المغربية مرحبا.",
    "goodbye": "بسلامة. إلى احتجتي شي معلومة على قانون الشغل رجع سولني.",
    "unclear": "ما فهمتش السؤال مزيان. عافاك وضح ليا واش كتهضر على خدمة، أجر، طرد، كونجي، CNSS، أو حادث شغل.",
}


@dataclass(frozen=True)
class DarijaIntentResult:
    intent: str
    normalized_query: str
    should_search_rag: bool
    confidence: float
    matched_by: str

    @property
    def is_legal(self) -> bool:
        return self.should_search_rag and self.intent not in NON_LEGAL_INTENTS


def normalize_text(text: str) -> str:
    text = text.casefold()
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
        "گ": "ك",
        "ڤ": "ف",
        "پ": "ب",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[\u064b-\u065f\u0670]", "", text)
    text = re.sub(r"[^\w\u0600-\u06ff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> set[str]:
    return {token for token in normalize_text(text).split() if len(token) > 1}


def normalized_term_matches(text_norm: str, term_norm: str) -> bool:
    if not term_norm:
        return False
    word_chars = r"A-Za-z0-9_\u0621-\u064A\u0660-\u0669\u0671-\u06D3\u06FA-\u06FF"
    if re.search(rf"[^{word_chars}]", term_norm):
        return term_norm in text_norm
    pattern = rf"(?<![{word_chars}]){re.escape(term_norm)}(?![{word_chars}])"
    return bool(re.search(pattern, text_norm, flags=re.IGNORECASE))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}") from exc
    return rows


@lru_cache(maxsize=1)
def load_intent_resources() -> dict[str, Any]:
    if not INTENTS_PATH.exists() or not EXAMPLES_PATH.exists():
        # Keep imports safe before the dataset is generated.
        return {
            "intents": {},
            "examples": [],
            "exact": {},
            "examples_by_intent": {},
        }

    intents_payload = json.loads(INTENTS_PATH.read_text(encoding="utf-8"))
    examples = load_jsonl(EXAMPLES_PATH)
    exact = {normalize_text(row["darija_question"]): row for row in examples}

    examples_by_intent: dict[str, list[dict[str, Any]]] = {}
    for row in examples:
        examples_by_intent.setdefault(row["intent"], []).append(
            {
                **row,
                "_normalized": normalize_text(row["darija_question"]),
                "_tokens": tokens(row["darija_question"]),
            }
        )

    return {
        "intents": intents_payload.get("intents", {}),
        "examples": examples,
        "exact": exact,
        "examples_by_intent": examples_by_intent,
    }


def keyword_score(question_norm: str, question_tokens: set[str], definition: dict[str, Any]) -> float:
    score = 0.0
    for keyword in definition.get("keywords", []):
        keyword_norm = normalize_text(str(keyword))
        if not keyword_norm:
            continue
        keyword_tokens = tokens(keyword_norm)
        if normalized_term_matches(question_norm, keyword_norm):
            score += 0.45 + min(len(keyword_tokens), 4) * 0.04
        elif keyword_tokens and keyword_tokens <= question_tokens:
            score += 0.35
        elif keyword_tokens and question_tokens & keyword_tokens:
            score += 0.10 * len(question_tokens & keyword_tokens)
    return score


def example_similarity(question_norm: str, question_tokens: set[str], examples: list[dict[str, Any]]) -> float:
    best = 0.0
    for example in examples[:80]:
        example_norm = example["_normalized"]
        ratio = SequenceMatcher(None, question_norm, example_norm).ratio()
        example_tokens = example["_tokens"]
        overlap = len(question_tokens & example_tokens) / max(len(question_tokens | example_tokens), 1)
        best = max(best, ratio * 0.65 + overlap * 0.35)
    return best


def contains_any(question_norm: str, terms: list[str]) -> bool:
    return any(normalize_text(term) in question_norm for term in terms)


def specific_intent_bonus(intent: str, question_norm: str) -> float:
    maternity_terms = ["حامل", "الحامل", "حمل", "ولادة", "أمومة", "امومة", "grossesse"]
    dismissal_terms = ["طرد", "فصل", "خرج", "رجعني", "رفض يرجعني", "بعد الولادة"]
    accident_terms = ["حادث", "حادثة", "تجرح", "تكسرت", "accident"]
    compensation_terms = ["تعويض", "تصريح", "حقوق", "شنو ندير"]
    cnss_terms = ["cnss", "ضمان", "تصريح", "مصرحش", "مسجلنيش", "cotisation"]
    non_declaration_terms = ["مصرحش", "ما مصرحش", "مسجلنيش", "تصريح", "ناقص"]
    abusive_terms = ["بلا سبب", "بدون سبب", "تعسفي", "ما عطاونيش سبب"]

    if intent == "maternity_protection" and contains_any(question_norm, maternity_terms):
        bonus = 0.55
        if contains_any(question_norm, dismissal_terms):
            bonus += 0.45
        return bonus
    if intent == "work_accident_compensation" and contains_any(question_norm, accident_terms):
        return 0.45 if contains_any(question_norm, compensation_terms) else 0.20
    if intent == "cnss_non_declaration" and contains_any(question_norm, cnss_terms):
        return 0.45 if contains_any(question_norm, non_declaration_terms) else 0.10
    if intent == "abusive_dismissal" and contains_any(question_norm, abusive_terms):
        return 0.45
    return 0.0


def intent_definition(intents: dict[str, dict[str, Any]], intent: str) -> dict[str, Any]:
    if intent in intents:
        return intents[intent]
    specific = SPECIFIC_INTENT_DEFINITIONS.get(intent, {})
    source_intent = specific.get("source_intent")
    source_definition = intents.get(str(source_intent), {})
    return {
        **source_definition,
        **{key: value for key, value in specific.items() if key != "source_intent"},
    }


def canonical_intent(intent: str, question_norm: str = "") -> str:
    if intent == "maternity" and (
        not question_norm
        or contains_any(question_norm, ["حامل", "الحامل", "حمل", "ولادة", "أمومة", "grossesse"])
    ):
        return "maternity_protection"
    return intent


def detect_darija_intent(question: str) -> DarijaIntentResult:
    resources = load_intent_resources()
    intents: dict[str, dict[str, Any]] = resources["intents"]
    exact: dict[str, dict[str, Any]] = resources["exact"]
    examples_by_intent: dict[str, list[dict[str, Any]]] = resources["examples_by_intent"]

    question_norm = normalize_text(question)
    if not question_norm:
        return DarijaIntentResult("unclear", "", False, 1.0, "empty")

    out_of_scope_hit = any(normalize_text(hint) in question_norm for hint in OUT_OF_SCOPE_HINTS)
    has_work_context = any(normalize_text(hint) in question_norm for hint in WORK_CONTEXT_HINTS)
    mentions_work_accident = (
        any(normalize_text(term) in question_norm for term in ("حادث", "حادثة", "accident", "طحت", "تجرحت"))
        and has_work_context
    )
    if out_of_scope_hit and not mentions_work_accident:
        definition = intents.get("out_of_scope", {})
        return DarijaIntentResult(
            "out_of_scope",
            str(definition.get("normalized_query", "خارج نطاق مدونة الشغل المغربية")),
            False,
            0.95,
            "out_of_scope_hint",
        )

    exact_row = exact.get(question_norm)
    if exact_row:
        intent = canonical_intent(exact_row["intent"], question_norm)
        definition = intent_definition(intents, intent)
        return DarijaIntentResult(
            intent=intent,
            normalized_query=str(definition.get("normalized_query") or exact_row.get("normalized_query", "")),
            should_search_rag=bool(exact_row.get("should_search_rag", False)),
            confidence=1.0,
            matched_by="exact",
        )

    question_token_set = tokens(question_norm)
    candidates: list[tuple[int, float, str, str]] = []

    intent_items = list(intents.items()) + [
        (intent, intent_definition(intents, intent))
        for intent in SPECIFIC_INTENT_DEFINITIONS
    ]

    for intent, definition in intent_items:
        score = keyword_score(question_norm, question_token_set, definition)
        score += example_similarity(question_norm, question_token_set, examples_by_intent.get(intent, []))
        score += specific_intent_bonus(intent, question_norm)

        if intent in DIRECT_INTENTS and len(question_token_set) <= 3:
            score += 0.12
        if intent == "out_of_scope" and score > 0.55:
            score += 0.20

        if score > 0:
            candidates.append((INTENT_PRIORITY.get(intent, 0), score, intent, "fuzzy_keyword"))

    if candidates:
        _, best_score, best_intent, best_reason = max(
            candidates,
            key=lambda item: (
                item[0] if item[1] >= 0.42 else -1,
                item[1],
            ),
        )
        best_intent = canonical_intent(best_intent, question_norm)
    else:
        best_intent = "unclear"
        best_score = 0.0
        best_reason = "fallback"

    if best_score < 0.42:
        best_intent = "unclear"
        best_score = max(best_score, 0.30)
        best_reason = "low_confidence"

    definition = intent_definition(intents, best_intent)
    return DarijaIntentResult(
        intent=best_intent,
        normalized_query=str(definition.get("normalized_query", "")),
        should_search_rag=best_intent not in NON_LEGAL_INTENTS,
        confidence=round(min(best_score, 0.99), 4),
        matched_by=best_reason,
    )


def direct_answer_for_intent(intent: str) -> str | None:
    if intent == "out_of_scope":
        return OUT_OF_SCOPE_MESSAGE
    return DIRECT_ANSWERS.get(intent)


def expand_question_with_intent(question: str, result: DarijaIntentResult | None = None) -> str:
    result = result or detect_darija_intent(question)
    if not result.is_legal or not result.normalized_query:
        return question
    normalized = normalize_text(question)
    expansion = result.normalized_query
    if normalize_text(expansion) in normalized:
        return question
    return f"{question} {expansion}"
