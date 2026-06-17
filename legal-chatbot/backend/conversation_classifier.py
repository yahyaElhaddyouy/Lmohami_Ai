# -*- coding: utf-8 -*-
"""Conversation-level routing before legal understanding and RAG."""

from __future__ import annotations

import re
from typing import Literal, TypedDict

try:
    from darija_intent import detect_darija_intent
except Exception:  # pragma: no cover - keeps this module usable in isolation.
    detect_darija_intent = None


ConversationType = Literal[
    "labor_law",
    "general_conversation",
    "greeting",
    "thanks",
    "non_labor_law_legal",
    "unknown",
]


class ConversationClassification(TypedDict):
    type: ConversationType
    confidence: float


ARABIC_DIACRITICS_RE = re.compile(r"[\u064b-\u065f\u0670]")

GENERAL_OVERRIDE_PHRASES = (
    "كيف داير مع العطلة",
    "بغيت نمشي لعطلة",
    "فين نمشي فالعطلة",
    "العطلة مع العائلة",
    "العطلة مع صحابي",
)

GREETINGS = {
    "السلام عليكم",
    "السلام",
    "سلام",
    "salam",
    "salam alikom",
    "salam alaikom",
    "bonjour",
    "hello",
    "hi",
    "صباح الخير",
    "مسا الخير",
    "مساء النور",
    "مرحبا",
    "ahlan",
    "labas",
    "sba7 lkhir",
    "سلام عليكم خويا",
    "salam khoya",
}

THANKS = {
    "شكرا",
    "شكرا بزاف",
    "بارك الله فيك",
    "يعطيك الصحة",
    "merci",
    "thanks",
    "thank you",
    "lah yhafdek",
    "lah yjazik bikhir",
    "chokran",
    "chokran bzaf",
    "الله يجازيك بخير",
    "مزيان شكرا",
    "merci khoya",
    "thx",
    "شكرا خويا",
}

LABOR_PHRASES = (
    "trdoni",
    "nsta9el",
    "isti9ala",
    "t7t f lkhdma",
    "tjre7t",
    "machine drbatni",
    "khdemt jouj chhor",
    "ma 3tawni walo",
    "ma khlsonich",
    "chahadat l3amal",
    "attestation",
    "ma tjich ghda",
    "7ydo smiti",
    "planning bla tafsir",
    "ana 7amla",
    "grossesse",
    "tbib 3tani repos",
    "kankhdem sa3at zayda",
    "heures sup",
    "accident travail",
    "resignation",
    "ma 3tawnich contrat",
    "messages m3a patron",
    "nthbet lkhdma",
    "khsmo lia",
    "mofatich choghl",
    "chikaya 3nd mofatich",
    "rab7 l9adiya 100",
    "ch7al ghadi nakhod bdebt",
    "patron gal lia ma tb9ach tji",
    "ma tb9ach tji",
    "sir trta7",
    "7ta n3ayto lik",
    "mrdt",
    "certificat medical",
    "khdam bla contrat",
    "bla contrat",
    "خدام بلا عقد",
    "بلا عقد مكتوب",
    "سير ترتاح حتى نعيطو ليك",
    "سير ترتاح",
    "حتى نعيطو ليك",
    "بقا فداركم",
    "ما خلصنيش",
    "ما خلصونيش",
    "ما تخلصتش",
    "ما عطانيش الصالير",
    "ما عطاونيش الصالير",
    "ما عطاوني والو",
    "ما عطاونيش كونطرا",
    "خدمت شهرين",
    "الصالير",
    "السالير",
    "الخلاص",
    "قالو ليا ما تبقاش تجي",
    "ما تبقاش تجي",
    "سير بحالك",
    "المسطرة قبل الطرد",
    "الطرد",
    "طردوني",
    "خرجوني من الخدمة",
    "حيدوني من الخدمة",
    "مخلاونيش ندخل",
    "منعوني ندخل",
    "ما خلاونيش نخدم",
    "ما قبلونيش نرجع",
    "منعني ندخل",
    "منعني ندخل نخدم",
    "منعني نخدم",
    "رفضو يرجعوني",
    "بغيت نستاقل",
    "نستاقل",
    "استاقل",
    "استقالة",
    "بغيت نمشي من الخدمة",
    "بغيت نخرج من الخدمة",
    "تجرحت فالعمل",
    "تجرحت فالورشة",
    "الماكينة ضرباتني",
    "فالسبيطار",
    "تكسرت فالخدمة",
    "تكسرت فالعمل",
    "ما مصرحش بيا",
    "ما مصرحينش بيا",
    "مصرحش بيا",
    "مفتشية الشغل",
    "مفتش الشغل",
    "حادث شغل",
    "حادثة شغل",
    "حادث داخل العمل",
    "حادث داخل الخدمة",
    "accident de travail",
    "inspection du travail",
    "شهادة العمل",
    "شهادة الشغل",
    "certificat de travail",
    "عطلة سنوية",
    "العطلة السنوية",
    "العطلة",
    "الإجازة",
    "الاجازة",
    "congé",
    "conge",
    "كونجي",
    "ساعات إضافية",
    "ساعات زايدة",
    "من بعد الوقت",
    "الساعات الإضافية",
    "الساعات الاضافية",
    "سوايع زايدة",
    "السوايع الزايدة",
    "الوقت العادي",
    "majoration",
    "heures supplémentaires",
    "الخطأ الجسيم",
    "محضر الاستماع",
    "مسطرة الفصل",
    "الأجر",
    "الاجر",
    "عدم أداء الأجر",
    "أجري",
    "اجري",
    "مرضت وغيبت",
    "غبت بالمرض",
    "المرض",
    "شهادة طبية",
    "certificat médical",
    "certificat medical",
    "الضمان الاجتماعي",
    "ما بان حتى شهر فالضمان",
    "عقد الشغل",
    "مساجات مع المشغل",
    "نثبت الخدمة",
    "إثبات عقد",
    "اثبات عقد",
    "relation de travail",
    "preuve",
    "مدونة الشغل",
    "قانون الشغل",
    "المادة",
    "الفصل",
    "article",
    "تعويض",
    "faute grave",
    "licenciement",
    "salaire",
    "cnss",
    "contrat",
    "بلا كونطرا",
    "عقد محدد المدة",
    "محدد المدة",
    "cdd",
    "cdi",
    "preavis",
    "préavis",
    "demission",
    "démission",
    "حيدو سميتي",
    "البلانينغ",
    "بدلو ليا البوست",
    "اقتطاع فالخلصة",
    "خصمو ليا",
    "شحال غادي ناخد بالضبط",
    "رابح القضية",
)

LABOR_CONTEXT_TERMS = (
    "المشغل",
    "الباطرون",
    "patron",
    "employeur",
    "الشركة",
    "الخدمة",
    "لخدمة",
    "الشغل",
    "الورشة",
    "travail",
    "hr",
)

LABOR_ACTION_TERMS = (
    "خلص",
    "صالير",
    "الأجر",
    "اجر",
    "طرد",
    "خرج",
    "حيد",
    "منع",
    "وقف",
    "عقد",
    "كونطرا",
    "تصريح",
    "ضمان",
    "cnss",
    "استقالة",
    "تعويض",
    "حادث",
    "تجرح",
    "تجرحت",
    "تكسرت",
    "مرض",
    "ولادة",
    "حامل",
)

NON_LABOR_LEGAL_TERMS = (
    "tala9",
    "nafa9a",
    "moul dar",
    "kira",
    "طلاق",
    "نفقة",
    "حضانة",
    "كراء",
    "مول الدار",
    "إرث",
    "ارث",
    "ميراث",
    "الورث",
    "التركة",
    "جنائي",
    "الشرطة",
    "البوليس",
    "محكمة تجارية",
    "دعوى تجارية",
    "شركة تجارية",
    "ضريبة",
    "ضرائب",
    "impots",
    "banque",
    "البنك",
    "العقار",
    "الحالة المدنية",
    "فيزا",
    "الهجرة",
    "حادثة سير",
    "الجار",
    "مخالفة",
    "قضية",
    "دعوى",
    "code route",
)

GENERAL_DARIJA_SIGNALS = (
    "شنو كتعني",
    "اش كتعني",
    "شنو معنى",
    "اش معنى",
    "واش كتفهم",
    "كتفهم",
    "فهمني",
    "فهم ليا",
    "fhemtini",
    "fhemni",
    "katfhem",
    "wach",
    "chno",
    "ch7al",
    "chhal",
    "fin",
    "3lach",
    "kifach",
    "ana",
    "bghit",
    "بغيت",
    "baghi",
    "m9ele9",
    "mkele9",
    "3yan",
    "t3yit",
    "z3fan",
    "far7an",
    "fer7an",
    "khayef",
    "bzaf",
    " بزاف",
    "دابا",
    "كازا",
    "مراكش",
    "الجو",
    "سخون",
    "برد",
    "نرتاح",
    "نهضر",
    "نحكي",
    "الدارجة",
    "دارجة",
    "مسمن",
    "حريرة",
    "العشا",
    "ماكلة",
    "طاكسي",
    "طوبيس",
    "التلفون",
    "القهوة",
    "السوق",
    "البحر",
    "سفر",
    "نسافر",
    "نمشي",
    "نتمشى",
    "نتقضى",
    "علاش",
    "فين",
    "شنو ندير",
    "لاباس",
    "تهلا",
    "واخا",
    "صافي",
    "ما فهمت والو",
    "ما فاهم والو",
    "ما فاهم",
    "ma fhemt walo",
    "lhala",
    "skhoun",
    "bared",
    "nrtah",
    "nhder",
    "m3ak",
    "mzyan",
    "walo",
    "lyoum",
    "daba",
    "fatigué",
    "stressé",
    "content",
    "météo",
    "bouchon",
    "occupé",
)


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
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = ARABIC_DIACRITICS_RE.sub("", text)
    text = re.sub(r"[^\w\u0600-\u06ff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_any(normalized: str, terms: tuple[str, ...] | set[str]) -> bool:
    return any(normalize_text(term) in normalized for term in terms)


def is_short_exact(normalized: str, terms: set[str]) -> bool:
    return normalized in {normalize_text(term) for term in terms}


def has_standalone_phrase(normalized: str, phrase: str) -> bool:
    normalized_phrase = normalize_text(phrase)
    if not normalized_phrase:
        return False
    return bool(
        re.search(
            rf"(?:^|\s){re.escape(normalized_phrase)}(?:$|\s)",
            normalized,
        )
    )


def is_wrapped_social_message(
    normalized: str,
    terms: set[str],
    *,
    allow_arabic_greeting_prefix: bool = False,
    allow_embedded: bool = False,
) -> bool:
    social_normalized = re.sub(r"[،؛؟]+", " ", normalized)
    social_normalized = re.sub(r"\s+", " ", social_normalized).strip()

    if is_short_exact(social_normalized, terms):
        return True

    candidate = social_normalized
    polite_prefix = normalize_text("عافاك الله يخليك")
    if candidate.startswith(f"{polite_prefix} "):
        candidate = candidate[len(polite_prefix) :].strip()

    for suffix in ("عافاك", "من فضلك"):
        normalized_suffix = normalize_text(suffix)
        if candidate.endswith(f" {normalized_suffix}"):
            candidate = candidate[: -len(normalized_suffix)].strip()

    if is_short_exact(candidate, terms):
        return True

    if allow_embedded and any(
        has_standalone_phrase(social_normalized, term) for term in terms
    ):
        return True

    return (
        allow_arabic_greeting_prefix
        and social_normalized.startswith(f"{normalize_text('السلام عليكم')} ")
    )


def classify_conversation(question: str) -> ConversationClassification:
    normalized = normalize_text(question)
    if not normalized or not re.search(r"[A-Za-z0-9\u0621-\u064A\u0660-\u0669]", normalized):
        return {"type": "unknown", "confidence": 0.2}

    if contains_any(normalized, GENERAL_OVERRIDE_PHRASES):
        return {"type": "general_conversation", "confidence": 0.82}

    labor_phrase_match = contains_any(normalized, LABOR_PHRASES)
    labor_context = contains_any(normalized, LABOR_CONTEXT_TERMS)
    labor_action = contains_any(normalized, LABOR_ACTION_TERMS)
    non_labor_legal = contains_any(normalized, NON_LABOR_LEGAL_TERMS)

    if labor_phrase_match or (labor_context and labor_action):
        return {"type": "labor_law", "confidence": 0.9 if labor_phrase_match else 0.78}

    if non_labor_legal:
        return {"type": "non_labor_law_legal", "confidence": 0.86}

    if is_wrapped_social_message(
        normalized,
        GREETINGS,
        allow_arabic_greeting_prefix=True,
        allow_embedded=True,
    ):
        return {"type": "greeting", "confidence": 0.95}

    if is_wrapped_social_message(normalized, THANKS, allow_embedded=True):
        return {"type": "thanks", "confidence": 0.95}

    if contains_any(normalized, GENERAL_DARIJA_SIGNALS):
        return {"type": "general_conversation", "confidence": 0.74}

    if detect_darija_intent is not None:
        intent = detect_darija_intent(question)
        if getattr(intent, "is_legal", False) and float(getattr(intent, "confidence", 0.0)) >= 0.55:
            return {
                "type": "labor_law",
                "confidence": min(0.86, max(0.7, float(intent.confidence))),
            }

    if 1 <= len(normalized.split()) <= 8:
        return {"type": "general_conversation", "confidence": 0.55}

    return {"type": "unknown", "confidence": 0.35}
