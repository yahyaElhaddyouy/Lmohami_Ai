import json
import os
import random
import re
import sys
from dataclasses import dataclass
from types import SimpleNamespace

import chromadb
import requests

from conversation_classifier import classify_conversation
from darija_intent import (
    detect_darija_intent,
    direct_answer_for_intent,
)
from legal_understanding import analyze_question

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.getenv("CHROMA_PATH", os.path.join(BASE_DIR, "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "legal_sources")

OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")

EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b")
N_RESULTS = int(os.getenv("RAG_N_RESULTS", "2"))
MAX_GENERATED_ANSWER_CHARS = int(os.getenv("RAG_MAX_ANSWER_CHARS", "1800"))
MIN_RELEVANCE_SCORE = int(os.getenv("RAG_MIN_RELEVANCE_SCORE", "4"))
RAG_DEBUG = os.getenv("RAG_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
USE_LEGAL_UNDERSTANDING = os.getenv("USE_LEGAL_UNDERSTANDING", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
USE_VERIFIED_RULES_FIRST = os.getenv("USE_VERIFIED_RULES_FIRST", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
CHAT_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "320"))

INSUFFICIENT_CONTEXT_MESSAGE = (
    "ما لقيتش جواب قانوني كافي فالمصدر المتوفر. "
    "هاد المساعد محدود فمدونة الشغل المغربية."
)

LEGAL_TOPIC_TERMS = {
    "preavis": [
        "préavis", "preavis", "délai de préavis", "delai de preavis",
        "إنذار", "انذار", "إشعار", "اشعار", "مدة الإخطار",
        "مدة الإنذار", "تعويض الإخطار", "indemnité de préavis",
        "بقا شهر", "شهر آخر", "نقطعو عليك", "باغي نمشي بلا مشاكل",
    ],
    "resignation": [
        "استقالة", "نستاقل", "استاقل", "démission", "demission",
        "resignation", "كتب استقالة", "نكتب استقالة", "وقعت resignation",
        "استقالة بالواتساب", "بغيت نستاقل", "بغيت نمشي من الخدمة",
        "استاقلش", "هددوني",
    ],
    "salary": [
        "الأجر", "اجر", "أجرة", "الصالير", "السالير", "خلصني",
        "ما خلصنيش", "ما تخلصتش", "ماعطانيش الصالير", "ما عطانيش الصالير",
        "الخلاص", "عدم أداء الأجر",
        "أجري", "اجري", "ما توصلتش", "بقا عند الشركة",
        "أجر غير مؤدى", "salaire", "rémunération", "remuneration",
        "paiement du salaire", "défaut de paiement du salaire",
        "خلصة", "الخلصة", "خصمو", "خصم", "اقتطاع", "prime",
        "bulletin", "retenue", "ما خلصونيش", "خلصونيش",
        "صبر حتى تدخل الفلوس",
    ],
    "overtime": [
        "الساعات الإضافية", "ساعات إضافية", "ساعة إضافية",
        "السوايع الزايدة", "ساعات زايدة", "heures supplémentaires",
        "heures supplementaires", "heures sup", "overtime", "majoration de salaire",
        "حتى 10", "10 دالليل", "بعد الوقت", "weekend", "weekends",
        "planning فيه ساعات", "أكثر من الوقت العادي",
    ],
    "sick_leave": [
        "مرض", "المرض", "مريض", "طبيب", "شهادة طبية",
        "غياب بسبب المرض", "رخصة مرضية", "maladie", "absence pour maladie",
        "certificat médical", "certificat medical", "arrêt", "arret",
        "repos", "السبيطار", "سبيطار", "absence", "مرضت",
        "بالمرض", "أكثر من أربعة أيام", "اكثر من اربعة ايام",
    ],
    "termination": [
        "طرد", "الطرد", "قبل الطرد", "مسطرة الطرد", "مسطرة الفصل",
        "طردوني", "فصل", "خروج", "بلا سبب", "سبب مقبول",
        "خرجني", "خرجوني", "سير بحالك", "ما يسمع ليا",
        "licenciement", "indemnité de licenciement",
        "dommages-intérêts", "تعويض", "الفصل",
        "حيدوني", "حيدو", "ما تجيش", "ما تبقاش تجي",
        "ما خلوونيش نرجع", "منعوني ندخل", "منعوني ندخل نخدم",
        "منعني ندخل", "منعني ندخل نخدم", "منعني نخدم",
        "سدّو عليا", "سدو عليا", "badge",
        "fin de contrat", "planning بلا تفسير", "shift الجديد", "البوست",
        "سير ترتاح", "ترتاح شوية", "سالينا معاك", "راه سالينا",
        "حتى نعيطو ليك", "بقا فداركم", "ما بقاوش كيردو",
    ],
    "work_certificate": [
        "شهادة العمل", "شهادة الشغل", "certificat de travail",
        "شهادة الخدمة", "شهادة ناقصة", "attestation",
        "رفضو يعطوني papier", "رفض يعطيني papier", "ورقة الخدمة",
    ],
    "disciplinary_procedure": [
        "مسطرة تأديبية", "الاستماع", "محضر الاستماع", "مسطرة الفصل",
        "procédure disciplinaire", "procedure disciplinaire",
        "être entendu", "proces-verbal", "procès-verbal",
    ],
    "gross_misconduct": [
        "خطأ جسيم", "الخطأ الجسيم", "faute grave", "بدون تعويض",
        "مسطرة تأديبية", "مسطرة التأديب", "محضر الاستماع", "sans préavis",
        "سرقة", "سرقت", "اعتراف", "convocation", "avertissement",
        "الاستماع", "للاستماع", "حضرتش للاستماع", "ما حضرتش",
        "محضر", "نفصلوك", "نوقع",
    ],
    "paid_leave": [
        "كونجي", "الكونجي", "رفض الكونجي", "عطلة", "العطلة",
        "العطلة ديالي", "إجازة", "اجازة", "سنوي",
        "العطلة السنوية", "congé annuel payé", "conge annuel paye",
        "congé annuel", "conge annuel", "congé", "conge",
        "jour et demi", "Article 231",
    ],
    "contract": [
        "CDD", "CDI", "عقد", "العقد", "contrat", "durée déterminée",
        "durée indéterminée", "contrat à durée déterminée",
        "contrat a duree determinee", "contrat à durée indéterminée",
        "contrat a duree indeterminee", "خدام بلا عقد", "بلا عقد",
        "كونطرا", "بلا كونطرا", "بcdd", "بcdi",
        "عقد مكتوب", "preuve de l'existence du contrat de travail",
        "preuve de relation de travail", "proof", "relation de travail",
        "إثبات عقد الشغل", "اثبات عقد الشغل", "إثبات عقد", "اثبات عقد",
        "جميع الوسائل", "وسائل الإثبات", "وسائل الاثبات",
        "شفوي", "غير شفوي", "بلا papier", "خدام cash",
        "contract temporaire", "temporaire", "période d'essai",
        "periode d'essai", "contrat فيه مدة", "خدام دائم",
    ],
    "maternity_leave": [
        "حمل", "المرأة الحامل", "الحامل", "مرضت بالحمل", "الولادة", "عطلة الولادة",
        "الحامل", "حامل", "حاملة", "انا حامل", "وأنا حامل", "وانا حامل",
        "حماية الحامل", "حقوق المرأة الحامل",
        "maternité", "maternite", "congé de maternité",
        "grossesse", "salariée en état de grossesse",
        "protection de la maternité",
    ],
    "notice_job_search": [
        "نغيب باش نقلب على خدمة", "نقلب على خدمة", "خلال مدة الإنذار",
        "البحث عن خدمة", "recherche d'un autre emploi",
        "permissions d'absence rémunérées", "article 48", "article 49",
    ],
    "working_time": [
        "وقت العمل", "ساعات العمل", "44 ساعة", "مدة العمل",
        "durée du travail", "2288 heures", "44 heures",
    ],
    "labor_inspection": [
        "مفتش الشغل", "مفتشية الشغل", "تفتيش الشغل", "التفتيش",
        "للتفتيش", "النزاعات",
        "inspecteur du travail", "inspection du travail", "inspection",
    ],
    "work_accident": [
        "حادث شغل", "حادثة شغل", "حادث داخل الخدمة",
        "حادث فالخدمة", "حادث فالعمل", "طاح عليا شي حاجة فالخدمة",
        "تكسرت فالخدمة", "تجرحت فالعمل", "accident de travail",
        "accident du travail", "accidents du travail",
        "maladie professionnelle", "risques professionnels",
        "طحت فالخدمة", "طحت", "تأذيت", "تاديت", "ضرباتني",
        "machine", "ماكينة", "الورشة", "فالطريق للخدمة",
        "الحادثة", "بالحادثة", "الحادث", "بعد الحادث",
        "تجرحت فالشركة",
    ],
    "cnss": [
        "cnss", "الضمان الاجتماعي", "تصريح", "التصريح",
        "ما تصرحتش", "ما تصرحش بيا", "ما مصرحش بيا", "مصرحش بيا",
        "ما مسجلنيش", "ما مصرحش",
        "caisse nationale de sécurité sociale", "الضمان", "فالضمان",
        "صرحو بيا", "صرحوا بيا",
    ],
}

TOPIC_ANCHORS = {
    "preavis": ("article 51", "indemnité de préavis"),
    "resignation": ("article 51", "préavis", "indemnité de préavis"),
    "salary": ("article 361", "défaut de paiement du salaire", "article 363"),
    "overtime": ("article 201", "heures supplémentaires", "majoration de salaire"),
    "sick_leave": ("article 271", "certificat médical"),
    "termination": ("article 63", "motif acceptable", "justification du licenciement"),
    "work_certificate": ("article 72", "certificat de travail"),
    "paid_leave": ("article 231", "congé annuel payé"),
    "contract": (
        "article 16",
        "article 18",
        "durée déterminée",
        "durée indéterminée",
        "preuve de l'existence du contrat de travail",
    ),
    "gross_misconduct": ("article 61", "article 62", "faute grave", "procès-verbal"),
    "maternity_leave": (
        "article 152",
        "article 159",
        "grossesse",
        "protection de la maternité",
    ),
    "notice_job_search": (
        "article 48",
        "article 49",
        "recherche d'un autre emploi",
    ),
    "working_time": ("durée du travail", "2288 heures"),
    "labor_inspection": ("inspection du travail", "inspecteur du travail"),
    "cnss": ("caisse nationale de sécurité sociale", "sécurité sociale", "cotisations"),
    "work_accident": (
        "accident du travail",
        "accidents du travail",
        "maladie professionnelle",
        "risques professionnels",
        "article 340",
        "article 341",
    ),
}

LEGAL_CONCEPT_MAP = {
    "حادث": [
        "حادث شغل",
        "accident de travail",
        "accident du travail",
        "إصابة مهنية",
        "CNSS",
        "تعويض",
    ],
    "طرد": [
        "فصل",
        "licenciement",
        "تعويض",
        "مسطرة تأديبية",
        "محضر الاستماع",
    ],
    "طردوني": [
        "فصل",
        "licenciement",
        "تعويض",
        "مسطرة تأديبية",
        "محضر الاستماع",
    ],
    "ما خلصنيش": [
        "الأجر",
        "salaire",
        "défaut de paiement du salaire",
    ],
    "الصالير": [
        "الأجر",
        "salaire",
        "défaut de paiement du salaire",
    ],
    "كونجي": [
        "العطلة السنوية",
        "congé annuel payé",
    ],
    "مرض": [
        "شهادة طبية",
        "maladie",
        "absence pour maladie",
    ],
    "مرضت": [
        "شهادة طبية",
        "maladie",
        "absence pour maladie",
    ],
    "ما تصرحتش": [
        "CNSS",
        "الضمان الاجتماعي",
        "تصريح",
    ],
    "خدام بلا عقد": [
        "contrat de travail",
        "CDI",
        "CDD",
        "preuve de l'existence du contrat de travail",
        "preuve de relation de travail",
    ],
    "relation de travail": [
        "contrat de travail",
        "preuve de l'existence du contrat de travail",
        "preuve de relation de travail",
    ],
    "proof": [
        "contrat de travail",
        "preuve de l'existence du contrat de travail",
        "preuve de relation de travail",
    ],
    "إثبات عقد": [
        "contrat de travail",
        "preuve de l'existence du contrat de travail",
        "preuve de relation de travail",
    ],
    "اثبات عقد": [
        "contrat de travail",
        "preuve de l'existence du contrat de travail",
        "preuve de relation de travail",
    ],
    "جميع الوسائل": [
        "contrat de travail",
        "preuve de l'existence du contrat de travail",
        "preuve de relation de travail",
    ],
    "خرجني": [
        "فصل",
        "licenciement",
        "تعويض",
        "مسطرة الفصل",
        "محضر الاستماع",
    ],
    "ما يسمع ليا": [
        "فصل",
        "licenciement",
        "مسطرة الفصل",
        "محضر الاستماع",
    ],
    "أجري": [
        "الأجر",
        "salaire",
        "défaut de paiement du salaire",
    ],
    "اجري": [
        "الأجر",
        "salaire",
        "défaut de paiement du salaire",
    ],
    "ما توصلتش": [
        "الأجر",
        "salaire",
        "défaut de paiement du salaire",
    ],
    "بقا عند الشركة": [
        "الأجر",
        "salaire",
        "défaut de paiement du salaire",
    ],
    "الحامل": [
        "protection de la maternité",
        "grossesse",
        "congé de maternité",
    ],
    "حامل": [
        "protection de la maternité",
        "grossesse",
        "congé de maternité",
    ],
    "السوايع الزايدة": [
        "heures supplémentaires",
        "majoration de salaire",
    ],
    "شهادة العمل": [
        "certificat de travail",
    ],
    "CNSS": [
        "الضمان الاجتماعي",
        "تصريح",
        "تعويضات",
    ],
}

LEGAL_CONCEPT_ALIASES = {
    "طاح": "حادث",
    "طحت": "حادث",
    "طيحت": "حادث",
    "تكسرت": "حادث",
    "تكسر": "حادث",
    "تجرحت": "حادث",
    "جرح": "حادث",
    "ماعطانيش الصالير": "ما خلصنيش",
    "ما عطانيش الصالير": "ما خلصنيش",
    "ماخلصنيش": "ما خلصنيش",
    "الاجر": "الصالير",
    "الأجر": "الصالير",
    "الكونجي": "كونجي",
    "رفض الكونجي": "كونجي",
    "ما تصرحش بيا": "ما تصرحتش",
    "ما مصرحش بيا": "ما تصرحتش",
    "مصرحش بيا": "ما تصرحتش",
    "بلا عقد": "خدام بلا عقد",
    "خدام بلا كونطرا": "خدام بلا عقد",
    "كونطرا": "خدام بلا عقد",
    "سوايع زايدة": "السوايع الزايدة",
    "ساعات إضافية": "السوايع الزايدة",
}

OUT_OF_SCOPE_TERMS = [
    "حادثة سير", "حادتة سير", "الطريق العام", "code de la route",
    "طلاق", "كراء", "كريت", "مول الدار", "تجارية", "تجاري", "دعوى تجارية",
    "البوليس", "الشرطة", "جنائي", "ميراث", "إرث", "ارث", "الهجرة",
    "كندا", "banque", "impôts", "impots", "ضريبة", "عقار",
]

WORK_RELATED_TERMS = [
    "خدمة",
    "الخدمة",
    "فالخدمة",
    "داخل الخدمة",
    "الشغل",
    "العمل",
    "عامل",
    "أجير",
    "اجير",
    "مشغل",
    "شركة",
    "حادث شغل",
    "حادثة شغل",
    "accident de travail",
    "employeur",
    "salarié",
    "travail",
]

CITATION_PATTERN = re.compile(r"\[المصدر\s+\d+،\s+الصفحة\s+[^\]]+\]")
ARTICLE_PATTERN = re.compile(r"\barticle\s+(\d+)\b", re.IGNORECASE)
UNSAFE_PHRASES = ("نضمن", "أكيد تربح")
UNSUPPORTED_ACTION_PHRASES = ("خاصك دير شكاية",)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass(frozen=True)
class SourceChunk:
    number: int
    page: str
    text: str
    source: str = "unknown"
    category: str = "unknown"
    source_type: str = "unknown"
    distance: float | None = None

    @property
    def citation(self) -> str:
        return f"[المصدر {self.number}، الصفحة {self.page}]"

    @property
    def source_label(self) -> str:
        if self.category == "unknown" and self.source == "unknown":
            return "unknown"
        return f"{self.category}/{self.source}"


def source_chunk_from_metadata(
    number: int,
    document: str,
    metadata: dict,
    distance: float | None = None,
) -> SourceChunk:
    metadata = metadata or {}
    return SourceChunk(
        number=number,
        page=str(metadata.get("page", "unknown")),
        text=document.strip().replace("\n\n", "\n"),
        source=str(metadata.get("source", "unknown")),
        category=str(metadata.get("category", "unknown")),
        source_type=str(metadata.get("source_type", "unknown")),
        distance=distance,
    )


def terminal_text(text: str):
    if os.getenv("RAG_FORCE_ARABIC_RESHAPE") != "1":
        return text
    if not arabic_reshaper or not get_display:
        return text
    return "\n".join(get_display(arabic_reshaper.reshape(line)) for line in text.splitlines())


def terminal_print(text: str = ""):
    print(terminal_text(text))


def get_embedding(text: str):
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def is_obviously_out_of_scope(question: str) -> bool:
    normalized = question.lower()
    has_out_scope = any(term.lower() in normalized for term in OUT_OF_SCOPE_TERMS)
    has_work_context = any(term.lower() in normalized for term in WORK_RELATED_TERMS)
    has_labor_topic = any(question_matches_topic(question, topic) for topic in LEGAL_TOPIC_TERMS)
    mentions_accident = "حادث" in normalized or "accident" in normalized

    if has_out_scope and (
        "ماشي شغل" in normalized
        or "ماشي على الخدمة" in normalized
        or "خارج الخدمة" in normalized
        or "سؤال ماشي على الخدمة" in normalized
    ):
        return True

    if mentions_accident and has_work_context:
        return False

    if has_work_context or has_labor_topic:
        return False

    return has_out_scope


def asks_for_specific_article(question: str) -> str | None:
    match = re.search(r"(?:المادة|الفصل|article|القانون\s+رقم)\s*(\d+)", question.lower())
    if not match:
        return None
    return match.group(1)


def term_matches_text(text: str, term: str) -> bool:
    """Match legal terms without treating a word fragment as a full concept."""
    normalized_text = text.lower()
    normalized_term = term.lower().strip()
    if not normalized_term:
        return False
    word_chars = r"A-Za-z0-9_\u0621-\u064A\u0660-\u0669\u0671-\u06D3\u06FA-\u06FF"
    if re.search(rf"[^{word_chars}]", normalized_term):
        return normalized_term in normalized_text
    pattern = rf"(?<![{word_chars}]){re.escape(normalized_term)}(?![{word_chars}])"
    return bool(re.search(pattern, normalized_text, flags=re.IGNORECASE))


def question_matches_topic(question: str, topic: str) -> bool:
    return any(term_matches_text(question, term) for term in LEGAL_TOPIC_TERMS[topic])


def matched_topics(question: str) -> list[str]:
    return [
        topic
        for topic in LEGAL_TOPIC_TERMS
        if question_matches_topic(question, topic)
    ]


def is_explicit_cnss_question(question: str) -> bool:
    normalized = question.lower()
    explicit_terms = (
        "cnss",
        "الضمان",
        "الضمان الاجتماعي",
        "فالضمان",
        "الصندوق الوطني",
        "مصرح",
        "مصرحين",
        "مصرحش",
        "تصرح",
        "تصرحت",
        "صرحو بيا",
        "صرحوا بيا",
        "مسجل",
        "مسجلني",
        "cotisation",
    )
    return any(term in normalized for term in explicit_terms)


def is_no_written_contract_question(question: str) -> bool:
    normalized = question.lower()
    markers = (
        "بلا عقد",
        "بلا كونطرا",
        "ما عطاونيش contrat",
        "بلا contrat",
        "شفوي",
        "بلا papier",
        "خدام cash",
        "messages",
        "واتساب",
        "بغيت نثبت",
        "contrat non écrit",
        "preuve relation de travail",
    )
    return any(marker in normalized for marker in markers)


def is_waiting_for_hr_callback_question(question: str) -> bool:
    normalized = question.lower()
    return (
        ("حتى نعيطو ليك" in normalized or "سير حتى نعيطو ليك" in normalized)
        and not question_matches_topic(question, "work_certificate")
    )


def is_labor_inspection_salary_question(question: str) -> bool:
    normalized = question.lower()
    inspection_terms = (
        "مفتشية الشغل",
        "مفتش الشغل",
        "تفتيش الشغل",
        "inspection",
        "inspecteur",
    )
    salary_terms = (
        "الأجر",
        "اجر",
        "أجر",
        "ما خلصنيش",
        "ما خلصونيش",
        "خلص",
        "صالير",
        "سالير",
        "خلصة",
        "salaire",
    )
    return any(term in normalized for term in inspection_terms) and any(
        term in normalized for term in salary_terms
    )


def is_contract_type_question(question: str) -> bool:
    normalized = question.lower()
    markers = (
        "cdd",
        "cdi",
        "temporaire",
        "période d'essai",
        "periode d'essai",
        "contrat فيه مدة",
        "contract temporaire",
        "خدام دائم",
        "فيه مدة",
    )
    return any(marker in normalized for marker in markers)


def expand_query(question: str) -> str:
    """Append Darija legal concepts before retrieval while keeping the original text."""
    normalized = question.lower()
    matched_concepts = []

    for keyword in LEGAL_CONCEPT_MAP:
        if keyword.lower() in normalized:
            matched_concepts.append(keyword)

    for alias, concept in LEGAL_CONCEPT_ALIASES.items():
        if alias.lower() in normalized:
            matched_concepts.append(concept)

    expansions = []
    for concept in dict.fromkeys(matched_concepts):
        expansions.extend(LEGAL_CONCEPT_MAP.get(concept, []))

    unique_expansions = []
    for expansion in dict.fromkeys(expansions):
        if expansion.lower() not in normalized:
            unique_expansions.append(expansion)

    if not unique_expansions:
        return question

    return f"{question} {' '.join(unique_expansions)}"


def expand_legal_query(question: str) -> str:
    expanded_question = expand_query(question)
    normalized = expanded_question.lower()
    expansions = []

    for terms in LEGAL_TOPIC_TERMS.values():
        if any(term.lower() in normalized for term in terms):
            expansions.extend(terms)

    if not expansions:
        return expanded_question

    unique_expansions = list(dict.fromkeys(expansions))
    return f"{expanded_question}\nFrench legal keywords: {'; '.join(unique_expansions)}"


def anchor_score(text: str, question: str) -> int:
    normalized_text = text.lower()
    score = 0
    for topic in matched_topics(question):
        for anchor in TOPIC_ANCHORS.get(topic, ()):
            if anchor.lower() in normalized_text:
                score += 12
    return score


def keyword_score(text: str, query: str) -> int:
    normalized_text = text.lower()
    expanded_query = expand_legal_query(query).lower()
    score = 0

    for term in re.findall(r"[\wÀ-ÿ]+(?:[-'][\wÀ-ÿ]+)?", expanded_query):
        if len(term) >= 4 and term in normalized_text:
            score += 1

    for terms in LEGAL_TOPIC_TERMS.values():
        if any(term.lower() in expanded_query for term in terms):
            for term in terms:
                if term.lower() in normalized_text:
                    score += 4

    return score


def dedupe_chunks_by_page(chunks: list[SourceChunk]) -> list[SourceChunk]:
    """Keep the strongest chunk per source page so returned sources stay useful."""
    best_by_page = {}
    for chunk in chunks:
        key = (chunk.category, chunk.source, chunk.page)
        current = best_by_page.get(key)
        if current is None:
            best_by_page[key] = chunk
            continue

        current_distance = float("inf") if current.distance is None else current.distance
        next_distance = float("inf") if chunk.distance is None else chunk.distance
        if next_distance < current_distance:
            best_by_page[key] = chunk

    return list(best_by_page.values())


def relevant_chunks(question: str, chunks: list[SourceChunk]) -> list[SourceChunk]:
    """Keep chunks supported by direct overlap or by a matched legal-topic anchor."""
    return [
        chunk
        for chunk in chunks
        if keyword_score(chunk.text, question) >= MIN_RELEVANCE_SCORE
        or anchor_score(chunk.text, question) > 0
    ]


def balance_labor_inspection_salary_sources(
    question: str,
    chunks: list[SourceChunk],
    n_results: int,
) -> list[SourceChunk]:
    """For inspection + wage questions, preserve both practical and code sources."""
    if not is_labor_inspection_salary_question(question) or n_results < 2:
        return chunks[:n_results]

    labor_chunk = next(
        (chunk for chunk in chunks if chunk_has_category(chunk, "labor_inspection")),
        None,
    )
    code_chunk = next(
        (
            chunk
            for chunk in chunks
            if chunk_has_category(chunk, "code_travail")
            and (chunk.page in {"125", "126"} or question_matches_topic(question, "salary"))
        ),
        None,
    )

    balanced = []
    for chunk in (labor_chunk, code_chunk):
        if chunk and all(existing.text != chunk.text for existing in balanced):
            balanced.append(chunk)

    for chunk in chunks:
        if len(balanced) >= n_results:
            break
        if all(existing.text != chunk.text for existing in balanced):
            balanced.append(chunk)

    return balanced[:n_results]


def add_keyword_results(collection, question: str, existing: list[SourceChunk]) -> list[SourceChunk]:
    seen_text = {chunk.text for chunk in existing}
    records = collection.get(include=["documents", "metadatas"])
    scored = []

    for doc, meta in zip(records["documents"], records["metadatas"]):
        score = keyword_score(doc, question)
        if score <= 0:
            continue
        scored.append((score, doc, meta))

    scored.sort(key=lambda item: item[0], reverse=True)

    chunks = list(existing)
    for score, doc, meta in scored:
        clean_doc = doc.strip().replace("\n\n", "\n")
        if clean_doc in seen_text:
            continue

        chunks.append(
            source_chunk_from_metadata(
                number=len(chunks) + 1,
                document=clean_doc,
                metadata=meta,
                distance=None,
            )
        )
        seen_text.add(clean_doc)

    return chunks


def retrieve_law(question: str, n_results: int = N_RESULTS) -> list[SourceChunk]:
    """Combine vector search and keyword search, then keep useful unique sources."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    expanded_question = expand_query(question)
    if RAG_DEBUG:
        terminal_print(f"Expanded query: {expanded_question}\n")
    query_embedding = get_embedding(expand_legal_query(expanded_question))

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(n_results * 3, 6),
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results.get("distances", [[]])[0]

    chunks = []
    for index, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
        distance = distances[index - 1] if index - 1 < len(distances) else None

        chunks.append(
            source_chunk_from_metadata(
                number=index,
                document=doc,
                metadata=meta,
                distance=distance,
            )
        )

    chunks = add_keyword_results(collection, expanded_question, chunks)
    chunks = dedupe_chunks_by_page(chunks)

    chunks.sort(
        key=lambda chunk: (
            source_category_score(chunk, question),
            anchor_score(chunk.text, expanded_question)
            + keyword_score(chunk.text, expanded_question),
            0 if chunk.distance is None else -chunk.distance,
        ),
        reverse=True,
    )

    selected = balance_labor_inspection_salary_sources(
        expanded_question,
        relevant_chunks(expanded_question, chunks),
        n_results,
    )
    selected_chunks = [
        SourceChunk(
            number=index,
            page=chunk.page,
            text=chunk.text,
            source=chunk.source,
            category=chunk.category,
            source_type=chunk.source_type,
            distance=chunk.distance,
        )
        for index, chunk in enumerate(selected, start=1)
    ]
    if RAG_DEBUG:
        sources = ", ".join(
            f"{chunk.source_label} p{chunk.page}" for chunk in selected_chunks
        ) or "none"
        terminal_print(f"Retrieved sources: {sources}\n")
    return selected_chunks


def context_has_article(article_number: str, chunks: list[SourceChunk]) -> bool:
    context = "\n".join(chunk.text for chunk in chunks).lower()

    patterns = [
        rf"\barticle\s+{re.escape(article_number)}\b",
        rf"\bart\.\s*{re.escape(article_number)}\b",
        rf"المادة\s+{re.escape(article_number)}\b",
    ]

    return any(re.search(pattern, context, flags=re.IGNORECASE) for pattern in patterns)


def contains_all(context: str, *terms: str) -> bool:
    return all(term.lower() in context for term in terms)


def chunk_has_category(chunk: SourceChunk, category: str) -> bool:
    chunk_category = getattr(chunk, "category", None)
    if isinstance(chunk_category, str) and chunk_category.lower() == category.lower():
        return True

    metadata = getattr(chunk, "metadata", None)
    if isinstance(metadata, dict):
        metadata_category = metadata.get("category")
        return (
            isinstance(metadata_category, str)
            and metadata_category.lower() == category.lower()
        )

    return False


def has_source_category(chunks: list[SourceChunk], category: str) -> bool:
    return any(chunk_has_category(chunk, category) for chunk in chunks)


def source_category_score(chunk: SourceChunk, question: str) -> int:
    score = 0
    preferred_pages = {
        "termination": {"34", "35"},
        "gross_misconduct": {"26", "34"},
        "salary": {"125", "126"},
        "overtime": {"79", "80"},
        "paid_leave": {"88", "89"},
        "preavis": {"31"},
        "resignation": {"31"},
        "contract": {"18", "19"},
        "maternity_leave": {"64", "65", "66"},
        "sick_leave": {"98"},
        "work_certificate": {"38"},
        "work_accident": {"9", "10", "13", "32", "118"},
    }
    for topic, pages in preferred_pages.items():
        if question_matches_topic(question, topic) and chunk.page in pages:
            score += 4
    if is_labor_inspection_salary_question(question):
        if chunk_has_category(chunk, "labor_inspection"):
            score += 10
        elif chunk_has_category(chunk, "code_travail") and chunk.page in {"125", "126"}:
            score += 6
    if is_explicit_cnss_question(question) and chunk_has_category(chunk, "cnss"):
        score += 3
    if question_matches_topic(question, "work_accident") and chunk_has_category(
        chunk, "work_accident"
    ):
        score += 3
    if question_matches_topic(question, "labor_inspection") and chunk_has_category(
        chunk, "labor_inspection"
    ):
        score += 2
    if is_no_written_contract_question(question) and chunk.page == "19":
        score += 4
    return score


def first_citation(chunks: list[SourceChunk]) -> str:
    return chunks[0].citation


def citation_for_match(chunks: list[SourceChunk], *terms: str) -> str:
    for chunk in chunks:
        normalized = chunk.text.lower()
        if all(term.lower() in normalized for term in terms):
            return chunk.citation
    return first_citation(chunks)


def refusal_answer() -> str:
    return INSUFFICIENT_CONTEXT_MESSAGE


def asks_for_legal_guarantee(question: str) -> bool:
    normalized = question.lower()
    guarantee_terms = (
        "نضمن",
        "ضمانة",
        "مضمونة",
        "رابح القضية",
        "غادي نربح",
        "أكيد نربح",
        "أكيد تربح",
        "محسومة",
        "حكم نهائي",
        "جواب نهائي",
        "نتيجة مضمونة",
        "شحال غادي ناخد بالضبط",
    )
    return any(term in normalized for term in guarantee_terms)


def legal_guarantee_refusal_answer() -> str:
    return (
        "ما يمكنش نعطيك ضمانة ولا نتيجة نهائية، حيث أي نزاع كيتبدل حسب الوثائق، "
        "الإثبات، المسطرة، وتقدير الجهة المختصة. نقدر نعاونك ترتب الوقائع، تجمع "
        "الأدلة، وتعرف الأسئلة اللي خاصك تسول، ولكن بلا وعد بالربح أو مبلغ محدد."
    )


def normalize_conversation_text(text: str) -> str:
    return re.sub(r"[^\w\u0600-\u06FF]+", " ", text.lower()).strip()


def has_legal_context_in_conversation(text: str) -> bool:
    normalized = normalize_conversation_text(text)
    legal_markers = (
        "خدمة",
        "الشغل",
        "عمل",
        "مشغل",
        "أجير",
        "اجير",
        "طرد",
        "خرجني",
        "فصل",
        "أجر",
        "اجر",
        "صالير",
        "خلاص",
        "خلص",
        "عقد",
        "كونطرا",
        "كونجي",
        "مرض",
        "حادث",
        "cnss",
        "ضمان",
        "سوايع",
        "شركة",
        "وثائق",
        "دليل",
        "إثبات",
        "اثبات",
        "accident",
        "travail",
        "company",
        "relation de travail",
        "proof",
    )
    return any(marker in normalized for marker in legal_markers)


def has_clear_out_of_scope_context(text: str) -> bool:
    normalized = normalize_conversation_text(text)
    out_of_scope_markers = (
        "طلاق",
        "كراء",
        "كريت",
        "مول الدار",
        "الدار",
        "الجار",
        "حادثة سير",
        "حادثه سير",
        "الطريق",
        "جنائي",
        "إرث",
        "ارث",
        "تجارية",
        "فيزا",
        "الهجرة",
        "كندا",
        "banque",
        "impôts",
        "impots",
        "ضريبة",
        "عقار",
        "البوليس",
        "الشرطة",
    )
    return any(marker in normalized for marker in out_of_scope_markers)


def should_treat_as_native_direct_answer(question: str, intent_result) -> bool:
    if intent_result.intent == "out_of_scope" and has_clear_out_of_scope_context(question):
        return True
    if intent_result.intent == "out_of_scope" and has_legal_context_in_conversation(question):
        return False
    return True


def conversation_router(question: str) -> str | None:
    """Handle lightweight chat turns without invoking retrieval or the LLM."""
    normalized = normalize_conversation_text(question)
    if not normalized:
        return None

    greetings = {
        "hi",
        "hello",
        "salam",
        "سلام",
        "السلام",
        "السلام عليكم",
        "bonjour",
    }
    thanks = {"شكرا", "شكراً", "merci", "thanks", "thank you", "بارك الله فيك"}
    goodbyes = {"bye", "باي", "مع السلامة", "إلى اللقاء", "الى اللقاء", "سلام"}
    identities = {"شكون نتا", "شكون انت", "من انت", "who are you"}
    capabilities = {"شنو تقدر دير", "اش تقدر دير", "what can you do"}
    unclear_short = {"ok", "واش", "شنو"}
    certainty_checks = {"واش متأكد", "متأكد", "are you sure", "واش نتيق فيك"}
    explain_more = {"شرح ليا كثر", "زيد شرح", "فصل ليا", "explain more"}
    examples = {"عطيني مثال", "مثال", "give me example"}
    documents = {
        "شنو نصيفط",
        "شنو نرسل",
        "شنو الوثائق",
        "شنو خاصني نجمع",
        "what should i send",
    }

    if normalized in greetings:
        return random.choice(
            [
                "سلام، مرحبا بيك. سولني على أي حاجة متعلقة بقانون الشغل المغربي.",
                "أهلا بيك. نقدر نعاونك فأسئلة قانون الشغل المغربي.",
                "مرحبا، عطيني سؤالك المتعلق بالشغل وغادي نحاول نعاونك.",
            ]
        )

    if normalized in thanks:
        return random.choice(
            [
                "العفو. إلا بغيتي شي توضيح آخر مرحبا.",
                "مرحبا بيك، أي وقت.",
                "العفو، نقدر نعاونك فأي سؤال متعلق بالشغل.",
            ]
        )

    if normalized in goodbyes or normalized.startswith("bye ") or normalized.startswith("باي "):
        return random.choice(
            [
                "مع السلامة. إلا احتجتي شي معلومة على قانون الشغل، رجع سولني.",
                "بسلامة، ومرحبا فاش تحتاج توضيح آخر.",
                "الله يعاونك. أي سؤال متعلق بالشغل أنا هنا.",
            ]
        )

    if normalized in identities or (
        "شكون" in normalized and ("نتا" in normalized or "انت" in normalized)
    ):
        return random.choice(
            [
                "أنا مساعد قانوني ذكي مخصص لمدونة الشغل المغربية. كنشرح المعلومات بطريقة مبسطة، وماشي محامي.",
                "أنا مساعد كيشرح قانون الشغل المغربي بطريقة مبسطة، مع الاعتماد على المصادر القانونية المتوفرة.",
                "أنا AI قانوني متخصص فقانون الشغل المغربي. نعاونك تفهم الحقوق والواجبات، ولكن ما كنقدمش استشارة قانونية رسمية.",
            ]
        )

    if normalized in capabilities or (
        "تقدر" in normalized and "دير" in normalized and "شنو" in normalized
    ):
        return random.choice(
            [
                "نقدر نعاونك فمواضيع بحال الطرد، العقد، CNSS، الأجر، العطلة، والساعات الإضافية.",
                "نشرح ليك حقوقك وواجباتك فقانون الشغل المغربي مع المصادر القانونية المتوفرة.",
                "نقدر نجاوب على أسئلة مرتبطة بالشغل، التعويضات، العقود، المرض، العطلة، والأجر.",
            ]
        )

    generic_rights_question = (
        "بغيت نعرف حقي" in normalized
        or "بغيت نعرف واش عندي حق" in normalized
        or "واش عندي حق ولا لا" in normalized
        or "شي حاجة ماشي واضحة" in normalized
    )
    if generic_rights_question and not matched_topics(normalized):
        return (
            f"{INSUFFICIENT_CONTEXT_MESSAGE} "
            "عافاك وضح ليا واش المشكل على الطرد، الأجر، العقد، الكونجي، CNSS، المرض، ولا حادثة شغل."
        )

    if normalized in certainty_checks or (
        "متأكد" in normalized or "نثق" in normalized or "نتيق" in normalized
    ):
        return random.choice(
            [
                "الجواب كيبقى مبني غير على المصدر اللي لقيتو فمدونة الشغل. إلا بغيتي، عطيني تفاصيل أكثر باش نراجع الحالة بدقة.",
                "كنحاول نربط كل جواب بالمصدر القانوني المتوفر. بلا وثائق الحالة، ما نقدرش نعطيك نتيجة نهائية.",
                "متأكد من حدود الجواب: هو توجيه مبني على المصدر، وماشي استشارة قانونية رسمية.",
            ]
        )

    if normalized in explain_more or ("شرح" in normalized and "كثر" in normalized):
        return (
            "نقدر نشرح أكثر، ولكن عطيني السؤال أو الحالة اللي بغيتي نفصل فيها: "
            "الطرد، الأجر، العقد، العطلة، CNSS، ولا شي موضوع آخر فالشغل."
        )

    if normalized in examples:
        return (
            "مثال ديال سؤال واضح: واش المشغل يقدر يطردني بلا سبب؟ "
            "أو: شنو ندير إلا ما خلصنيش الصالير؟"
        )

    asks_for_documents = normalized in documents or (
        "وثائق" in normalized or "نصيفط" in normalized or "نجمع" in normalized
    )
    if asks_for_documents and not has_legal_context_in_conversation(normalized):
        return (
            "غالبا جمع العقد أو ما يثبت الخدمة، كشوفات الأداء، الرسائل، محضر الاستماع إن وجد، "
            "وأي وثيقة فيها التاريخ والسبب. ومن بعد سولني على الحالة بالتفاصيل."
        )

    if normalized in unclear_short:
        return random.choice(
            [
                "كتب ليا السؤال بشوية ديال التفاصيل باش نقدر نعاونك مزيان.",
                "عطيني شوية تفاصيل: واش السؤال على العقد، الأجر، الطرد، العطلة، ولا شي موضوع آخر فالشغل؟",
                "مازال السؤال ناقص شوية. شرح ليا الحالة ديالك فالشغل ونحاول نعطيك جواب واضح.",
            ]
        )

    if False and question_matches_topic(question, "labor_inspection") and has_source_category(
        chunks, "labor_inspection"
    ):
        first_source = next(
            chunk.citation for chunk in chunks if chunk_has_category(chunk, "labor_inspection")
        )
        return brief_answer(
            "إلى بغيتي تمشي لمفتشية الشغل، ركز على عرض الوقائع والوثائق بشكل واضح ومهني، وخلي الشكاية مرتبطة بمشكل الشغل المحدد.",
            [
                "مفتشية الشغل كتعاون فالتواصل، التوجيه، ومحاولة تسوية بعض نزاعات الشغل حسب المعطيات المتوفرة.",
                "خاصك توضّح شكون المشغل، نوع المشكل، التواريخ، وشنو طلبتي من الشركة قبل ذلك.",
                "ما تعطيش وعود أو اتهامات بلا دليل؛ خليك فالأحداث والوثائق.",
            ],
            first_source,
            "عمليا، حضر العقد أو أي دليل على الخدمة، كشوفات الأجر، الرسائل، وأي قرار مكتوب، ودير ملخص قصير بالترتيب الزمني.",
        )

    return None


def general_darija_meaning(question: str) -> str:
    normalized = normalize_conversation_text(question)
    lowered = question.lower()
    meaning = ""

    if ("الجو" in normalized and "سخون" in normalized) or "jaw skhoun" in lowered:
        meaning = "فهمت: كتقول باللي الجو سخون بزاف وما قدرتيش تخرج."
    elif "m9ele9" in lowered or "mkele9" in lowered or "مقلق" in normalized or "قلق" in normalized:
        meaning = "فهمت: كيبان أنك مقلق بزاف وما فاهمش الأمور مزيان دابا."
    elif ("دابا" in normalized and "نجي" in normalized) or "daba nji" in lowered:
        meaning = "فهمت: كتقصد دابا غادي نجي عندك أو نلتحق بيك."
    elif "lhala m9ewda" in lowered or ("الحالة" in normalized and "صعيبة" in normalized):
        meaning = "فهمت: كتقول أن الحالة صعيبة أو مقلقة شوية."
    elif "نرتاح" in normalized or "nrtah" in lowered:
        meaning = "فهمت: كتقول أنك بغيتي غير ترتاح شوية."
    elif "كازا" in normalized or "casa" in lowered:
        meaning = "فهمت: كتسول واش كنعرَف كازا، يعني الدار البيضاء."
    elif "ضغط" in normalized or "kayضغط" in lowered:
        meaning = "فهمت: كتقول أن كاين ضغط عليك وهاد الشي عياك."
    elif "message" in lowered or "مساج" in normalized:
        meaning = "فهمت: كتسول واش هاد الرسالة باين فيها مشكل أو محتاجة توضيح."
    else:
        meaning = f"فهمت الرسالة بالدارجة: {question.strip()}"

    return (
        f"{meaning} "
        "إلى كان هاد الكلام مرتبط بمشكل فالشغل، زيد شرح ليا شنو وقع والوثائق اللي عندك. "
        "إلى كان غير حديث عام، نقدر نفهم المعنى العام، ولكن التوجيه المتخصص ديالي محدود فمدونة الشغل المغربية."
    )


def normal_darija_response(question: str, classification: dict) -> str:
    """Answer non-labor turns directly, without legal retrieval."""
    conversation_type = classification.get("type")

    if conversation_type in {"greeting", "thanks"}:
        routed = conversation_router(question)
        if routed:
            return routed

    if conversation_type == "greeting":
        return "سلام، مرحبا بيك. نقدر نفهم الدارجة ونعاونك خصوصا فأسئلة مدونة الشغل المغربية."

    if conversation_type == "thanks":
        return "العفو، مرحبا بيك. إلى كان عندك سؤال على الشغل فالمغرب سولني."

    if conversation_type == "non_labor_law_legal":
        return (
            "ما لقيتش جواب قانوني كافي فالمصدر المتوفر. فهمت السؤال، ولكن هاد الموضوع قانوني خارج تخصصي فمدونة الشغل المغربية. "
            "نقدر نعاونك غير إلا كان المشكل مرتبط بالخدمة، الأجر، العقد، CNSS، الطرد، العطلة، أو حادثة شغل."
        )

    if conversation_type == "unknown":
        return (
            "مازال ما واضحش ليا شنو بغيتي بالضبط. "
            "إلى كان عندك مشكل فالشغل، شرح ليا شنو وقع: الأجر، الطرد، العقد، CNSS، العطلة، أو حادثة شغل."
        )

    return general_darija_meaning(question)


def should_use_full_structure(question: str) -> bool:
    """Verified legal answers now use one complete compact layout."""
    return False


def uncertainty_confidence(question: str, intent) -> str:
    """Map detector confidence to a small label used by prompts and safeguards."""
    detector_confidence = getattr(intent, "confidence", 1.0)
    if detector_confidence >= 0.8:
        return "high"
    if detector_confidence >= 0.55:
        return "medium"
    return "low"


def build_clarification_question(intent) -> str:
    intent_name = getattr(intent, "intent", str(intent))
    questions = {
        "dismissal": "واش عطاوك سبب مكتوب ولا غير شفوي؟",
        "abusive_dismissal": "واش عطاوك سبب مكتوب ولا غير شفوي؟",
        "disciplinary_dismissal": "واش عطاوك سبب مكتوب ولا غير شفوي؟",
        "salary_unpaid": "واش كاين تأخير ولا ما خلصوكش نهائياً؟",
        "work_accident": "واش وقع الحادث داخل الخدمة ولا خارجها؟",
        "work_accident_compensation": "واش وقع الحادث داخل الخدمة ولا خارجها؟",
        "cnss": "واش قلبتي ف CNSS وما لقيتيش التصريح ولا غير قالو ليك؟",
        "cnss_non_declaration": "واش قلبتي ف CNSS وما لقيتيش التصريح ولا غير قالو ليك؟",
        "maternity_protection": "واش عندك شهادة طبية أو شي وثيقة كتثبت الحمل أو تاريخ الولادة؟",
        "annual_leave": "واش طلبتي الكونجي ورفضوه ولا ما طلبتيش؟",
        "contract_cdd_cdi": "واش عندك شي وثيقة أو دليل على الخدمة؟",
        "no_written_contract": "واش عندك شي وثيقة أو دليل على الخدمة؟",
        "sick_leave": "واش عطيتي شهادة طبية للمشغل؟",
    }
    return questions.get(intent_name, "شنو التفاصيل الإضافية اللي تقدر توضحها؟")


def build_uncertainty_prefix(question: str, intent) -> tuple[str, str]:
    """Add conditional language when the original facts are incomplete."""
    detector_confidence = getattr(intent, "confidence", 1.0)
    if detector_confidence >= 0.8:
        return "", "high"

    confidence = uncertainty_confidence(question, intent)
    if confidence == "high":
        return "", confidence

    intent_name = getattr(intent, "intent", str(intent))
    if intent_name in {"dismissal", "disciplinary_dismissal", "abusive_dismissal"}:
        prefix = "إلى كان المشغل منعك ترجع للخدمة بشكل نهائي، فالقانون كيهضر على مسطرة وشروط قبل أي خلاصة."
    elif intent_name in {"work_accident", "work_accident_compensation"}:
        prefix = "إلا كان المقصود أن الإصابة وقعات أثناء الخدمة أو بسببها، فالقانون كيهضر على حادث شغل."
    elif intent_name == "maternity_protection":
        prefix = "إلا كان المقصود حماية الحمل أو الرجوع بعد الولادة، فالجواب خاصو يتربط بالشهادة الطبية والتواريخ والوثائق."
    elif intent_name == "cnss_non_declaration":
        prefix = "إلا كان المقصود أن المشغل كيقتطع أو كيهضر على CNSS ولكن التصريح ما باينش، خاص نراجعو وضعية التصريح والوثائق."
    elif intent_name in {"contract_cdd_cdi", "no_written_contract"}:
        prefix = "إلا ما كانش عندك عقد مكتوب، خاصنا نشوفو شنو كاين من دلائل الخدمة قبل أي خلاصة."
    else:
        prefix = "إلا كانت هادي هي الوقائع المقصودة، فالجواب القانوني كيبقى مشروط بالتفاصيل والوثائق."

    question_is_too_short = len(normalize_conversation_text(question).split()) <= 3
    if confidence == "low" or question_is_too_short:
        clarification = build_clarification_question(intent)
        prefix = f"{prefix}\n\nباش نعطيك جواب أدق، {clarification}"

    return prefix, confidence


def apply_uncertainty_prefix(answer: str, prefix: str) -> str:
    if not prefix:
        return answer
    if answer.startswith(prefix):
        return answer
    structured_start = "فهمت الحالة:\n"
    if answer.startswith(structured_start):
        return answer.replace(structured_start, f"{structured_start}{prefix}\n\n", 1)
    return f"{prefix}\n\n{answer}"


def soften_uncertain_answer(answer: str, question: str, confidence: str) -> str:
    """Remove legal conclusions that are too strong for sparse facts."""
    if confidence == "high":
        return answer

    normalized_question = normalize_conversation_text(question)
    mentions_gross_misconduct = (
        "خطأ جسيم" in normalized_question
        or "faute grave" in normalized_question
        or "غلط كبير" in normalized_question
    )

    softened_lines = []
    for line in answer.splitlines():
        normalized_line = normalize_conversation_text(line)
        if not mentions_gross_misconduct and (
            "خطأ جسيم" in normalized_line
            or "الخطأ الجسيم" in normalized_line
            or "faute grave" in normalized_line
        ):
            continue
        softened_lines.append(line)

    softened = "\n".join(softened_lines)
    replacements = {
        "تم فصلك": "إلى كان وقع إنهاء للعلاقة ديال الشغل",
        "أنت مطرود": "إلى كان المشغل منعك ترجع للخدمة بشكل نهائي",
        "انت مطرود": "إلى كان المشغل منعك ترجع للخدمة بشكل نهائي",
    }
    for source, target in replacements.items():
        softened = softened.replace(source, target)

    return re.sub(r"\n{3,}", "\n\n", softened).strip()


def brief_answer(
    direct_answer: str,
    points: list[str],
    citation: str,
    practical_note: str | None = None,
) -> str:
    """Build a complete but compact legal answer for verified rules."""
    key_points = [point.strip() for point in points if point.strip()]
    key_points.extend(
        [
            "النتيجة النهائية كتبدل حسب السبب المكتوب، التواريخ، والوثائق اللي عندك.",
            "ما نعتمدوش على الكلام الشفوي بوحدو إلا كان ممكن نثبتو الأمور كتابة.",
        ]
    )
    key_points = list(dict.fromkeys(key_points))[:5]

    practical_steps = [
        "جمع العقد أو أي دليل على الخدمة، وكشوفات الأداء، وأي مراسلات مع المشغل.",
        "طلب توضيح مكتوب من المشغل وخلي نسخة من الطلب والجواب.",
    ]
    if practical_note:
        practical_steps.insert(0, practical_note.strip())
    practical_steps.append(
        "إلا بقات الحالة غير واضحة، تواصل مع مفتشية الشغل أو الجهة المختصة حسب الموضوع."
    )
    practical_steps = list(dict.fromkeys(practical_steps))[:5]

    return "\n\n".join(
        [
            "فهمت الحالة:\n"
            "حسب المعطيات اللي عطيتيني، السؤال كيتعلق بحق من حقوقك فالشغل وخصو يتراجع على ضوء الوثائق والسبب الحقيقي.",
            f"الجواب القانوني:\n{direct_answer.strip()}",
            "شنو مهم تعرف:\n" + "\n".join(f"- {point}" for point in key_points),
            "شنو تدير دابا:\n" + "\n".join(f"- {step}" for step in practical_steps),
            f"المصادر:\nالمصدر: {citation}",
            "تنبيه:\nهاد الجواب للتوجيه فقط وماشي استشارة قانونية رسمية.",
        ]
    )


def source_pages(chunks: list[SourceChunk]) -> set[str]:
    return {chunk.page for chunk in chunks}


def verified_source_subset(question: str, chunks: list[SourceChunk]) -> list[SourceChunk]:
    """Return the most useful cited pages for deterministic answers."""
    if is_labor_inspection_salary_question(question):
        selected = balance_labor_inspection_salary_sources(question, chunks, N_RESULTS)
        return selected or chunks
    if is_explicit_cnss_question(question) and has_source_category(chunks, "cnss"):
        selected = [chunk for chunk in chunks if chunk_has_category(chunk, "cnss")]
        return selected or chunks
    if question_matches_topic(question, "work_accident") and has_source_category(
        chunks, "work_accident"
    ):
        selected = [chunk for chunk in chunks if chunk_has_category(chunk, "work_accident")]
        return selected or chunks

    preferred_pages = {
        "salary": {"125", "126"},
        "overtime": {"79", "80"},
        "work_certificate": {"38"},
        "sick_leave": {"98"},
        "termination": {"34", "35"},
        "gross_misconduct": {"26", "34"},
        "preavis": {"31"},
        "resignation": {"31"},
        "paid_leave": {"88"},
        "contract": {"18", "19"},
        "maternity_leave": {"64", "65", "66"},
        "notice_job_search": {"30", "31"},
        "work_accident": {"32", "118"},
        "cnss": {"45", "129"},
    }

    keep_pages = set()
    for topic in matched_topics(question):
        keep_pages.update(preferred_pages.get(topic, set()))

    selected = [chunk for chunk in chunks if chunk.page in keep_pages]
    return selected or chunks


def answer_from_verified_rules(
    question: str,
    chunks: list[SourceChunk],
    original_question: str | None = None,
) -> str | None:
    """Return source-backed answers for high-risk recurring legal questions."""
    if not chunks:
        return None

    context = "\n".join(chunk.text for chunk in chunks).lower()
    first_source = first_citation(chunks)
    user_question = original_question or question
    topic_question = user_question

    if is_waiting_for_hr_callback_question(user_question):
        return brief_answer(
            "واش بغيتي شهادة العمل ولا كيهضرو معاك على الرجوع للخدمة؟ هاد التفصيل مهم باش نفرقو بين وثيقة نهاية الخدمة وبين توقف أو منع من الرجوع.",
            [
                "إلا كان المقصود شهادة العمل، خاص نعرفو واش عقد الشغل سالا فعلا ولا باقي غير كاين تماطل.",
                "إلا كان المقصود الرجوع للخدمة، خاص نعرفو واش عطاوك سبب مكتوب ولا غير قالوها شفوي.",
                "ما نحسموش واش هادي شهادة عمل أو طرد حتى توضّح شنو طلبتي وشنو قالو ليك بالضبط.",
            ],
            first_source,
            "عمليا، صيفط طلب مكتوب قصير: واش القرار نهائي؟ واش خاصني نرجع للخدمة؟ واش غادي تسلموني شهادة العمل إذا سالات العلاقة؟ واحتافظ بالجواب.",
        )

    if question_matches_topic(topic_question, "work_accident") and "accident du travail" in context:
        first_source = citation_for_match(chunks, "accident du travail")
        return brief_answer(
            "إلا وقع ليك حادث داخل الخدمة، المصدر كيهضر على توثيق ظروف حادث الشغل وإرسال تقرير للجهات المختصة.",
            [
                "خاص التقرير يبين ظروف الحادث أو المرض المهني.",
                "المصدر كيهضر على إرسال نسخة داخل 15 يوم من بعد الحادث أو constat ديال المرض المهني.",
            ],
            first_source,
            "عمليا، جمع الشهادة الطبية، أي شهود أو صور، وأي مراسلة مع المشغل.",
        )

    if question_matches_topic(user_question, "gross_misconduct") and contains_all(
        context,
        "article 61",
        "article 62",
    ):
        first_source = citation_for_match(chunks, "article 62")
        return brief_answer(
            "فالخطأ الجسيم، المدونة كتربط الفصل بمسطرة خاصة، وماشي غير قرار شفوي.",
            [
                "Article 61 كيهضر على إمكانية الفصل بلا préavis ولا تعويض فحالة الخطأ الجسيم.",
                "قبل الفصل، خاص الأجير يقدر يدافع على راسو ويتسمع ليه، ويتدار محضر.",
            ],
            first_source,
            "عمليا، طلب نسخة من محضر الاستماع وسبب الفصل المكتوب واحتافظ بأي مراسلة.",
        )

    if question_matches_topic(topic_question, "gross_misconduct") and has_source_category(
        chunks, "code_travail"
    ):
        first_source = first_citation(chunks)
        return brief_answer(
            "إلا كان الموضوع فيه استدعاء للاستماع، محضر، أو اتهام بخطأ جسيم، ما خاصوش يتحول لقرار نهائي بلا ما تفهم السبب والوثائق.",
            [
                "خاص نفرقو بين مجرد اتهام وبين قرار فصل مكتوب ومعلل.",
                "طلب نسخة من الاستدعاء أو المحضر، وما توقعش على اعتراف ما فاهموش.",
                "النتيجة كتبدل حسب واش دازت مسطرة الاستماع وشنو مكتوب فالوثائق.",
            ],
            first_source,
            "عمليا، جمع convocation، المحضر، أي رسائل، وأسماء الشهود إن وجدو، وطلب السبب مكتوب.",
        )

    if question_matches_topic(topic_question, "contract") and (
        "preuve de l'existence du contrat de travail" in context
        or "peut être rapportée par tous les moyens" in context
        or "article 18" in context
    ):
        first_source = citation_for_match(chunks, "article 18")
        if is_no_written_contract_question(user_question) and not is_contract_type_question(user_question):
            return brief_answer(
                "إلا كنت خدام بلا عقد مكتوب، هادشي ما كيعنيش بالضرورة ما كايناش علاقة شغل.",
                [
                    "المصدر كينص أن إثبات وجود عقد الشغل يمكن يكون بجميع وسائل الإثبات.",
                    "العقد المكتوب مفيد، ولكن الإثبات ماشي محصور فيه فقط.",
                ],
                first_source,
                "عمليا، جمع كشوفات الأداء، الرسائل، الشهود، بطاقة العمل إن وجدت، وأي دليل على الخدمة.",
            )

    if (
        question_matches_topic(topic_question, "contract")
        and is_no_written_contract_question(user_question)
        and not is_contract_type_question(user_question)
        and has_source_category(chunks, "code_travail")
    ):
        first_source = first_citation(chunks)
        return brief_answer(
            "إلا كنت خدام بلا عقد مكتوب أو عندك غير رسائل، ما نحسموش الوضعية من الكلام فقط، ولكن خاص نجمعو دلائل علاقة الشغل ونقراوها مع المصدر المتوفر.",
            [
                "الوثائق العملية بحال الرسائل، كشوفات الأداء، الحضور، أو الشهود كتعاون تفهم العلاقة الفعلية.",
                "العقد المكتوب كيعاون بزاف، ولكن غيابو ما خاصوش يخليك توقف عن جمع الدليل.",
                "النتيجة كتبدل حسب شنو كاين فالوثائق وشنو يقدر يتثبت.",
            ],
            first_source,
            "عمليا، جمع الواتسابات، أي badge أو planning، كشوفات الأداء، وأسماء الشهود، وطلب توضيح مكتوب من المشغل.",
        )

    if question_matches_topic(topic_question, "contract") and is_contract_type_question(user_question):
        first_source = first_citation(chunks)
        if "cdi" in user_question.lower():
            return brief_answer(
                "CDI هو عقد شغل غير محدد المدة، يعني ما فيهش تاريخ نهاية محدد من الأول.",
                [
                    "كيبقى العقد مستمر حتى يسالي بطريقة قانونية بحال اتفاق، استقالة، أو فصل مع احترام الشروط القانونية.",
                    "المهم هو تمييزه على CDD اللي كيكون محدد المدة أو مرتبط بحالات محددة.",
                ],
                first_source,
            )
        return brief_answer(
            "CDD هو عقد شغل محدد المدة، يعني كيتربط بمدة أو حالة محددة.",
            [
                "خاص الحالات والمدة تكون واضحة ومبررة حسب القواعد اللي كتنظم عقود الشغل.",
                "إلى استمر العمل خارج الإطار المتفق عليه، خاص الحالة تتراجع حسب الوثائق والوقائع.",
            ],
            first_source,
        )

    if is_explicit_cnss_question(question) and has_source_category(chunks, "cnss"):
        first_source = next(
            chunk.citation for chunk in chunks if chunk_has_category(chunk, "cnss")
        )
        return brief_answer(
            "إلا كان المشغل كينقص ليك اقتطاعات CNSS ولكن ما باينش التصريح ديالك، خاص أول خطوة هي تتأكد من وضعية التصريح عند CNSS.",
            [
                "جمع كشوفات الأداء اللي باينين فيها الاقتطاعات، العقد إلا كان، وأي دليل على الخدمة بحال الرسائل أو شهادة العمل أو الحضور.",
                "إلا عندك رقم CNSS أو أي وثيقة مرتبطة به، احتافظ بها باش تسهل التحقق.",
                "طلب من المشغل توضيح مكتوب على التصريح والاقتطاعات، وخلي التواصل موثق.",
                "إلا بقات الوضعية غير واضحة، تواصل مع CNSS للتحقق، ويمكن كذلك ترجع لمفتشية الشغل حسب الحالة.",
                "ما نقدرش نأكد عقوبات أو مبالغ محددة إلا إذا كانت مدعومة مباشرة بالمصدر المسترجع.",
            ],
            first_source,
        )

    if is_explicit_cnss_question(question) and contains_all(
        context,
        "caisse nationale",
        "sécurité sociale",
    ):
        first_source = citation_for_match(chunks, "caisse nationale")
        return brief_answer(
            "المصدر المتوفر كيهضر على CNSS والاشتراكات، ولكن ما فيهش تفاصيل كافية باش نشرح مسطرة عدم التصريح كاملة.",
            [
                "نقدر نقول غير أن CNSS واردة فالسياق ديال الالتزامات والوثائق المرتبطة بالشغل.",
                "باش نعطيك جواب أدق على عدم التصريح، خاص مصدر CNSS مباشر أو وثائق الحالة.",
            ],
            first_source,
            "عمليا، جمع العقد أو ما يثبت الخدمة، كشوفات الأداء، ورقم CNSS إلا كان عندك.",
        )

    if question_matches_topic(topic_question, "labor_inspection") and has_source_category(
        chunks, "labor_inspection"
    ):
        first_source = next(
            chunk.citation for chunk in chunks if chunk_has_category(chunk, "labor_inspection")
        )
        return brief_answer(
            "إلى بغيتي تمشي لمفتشية الشغل، ركز على عرض الوقائع والوثائق بشكل واضح ومهني، وخلي الشكاية مرتبطة بمشكل الشغل المحدد.",
            [
                "مفتشية الشغل كتعاون فالتواصل، التوجيه، ومحاولة تسوية بعض نزاعات الشغل حسب المعطيات المتوفرة.",
                "خاصك توضّح شكون المشغل، نوع المشكل، التواريخ، وشنو طلبتي من الشركة قبل ذلك.",
                "ما تعطيش وعود أو اتهامات بلا دليل؛ خليك فالأحداث والوثائق.",
            ],
            first_source,
            "عمليا، حضر العقد أو أي دليل على الخدمة، كشوفات الأجر، الرسائل، وأي قرار مكتوب، ودير ملخص قصير بالترتيب الزمني.",
        )

    if question_matches_topic(topic_question, "paid_leave") and "article 231" in context:
        first_source = citation_for_match(chunks, "article 231")
        if not should_use_full_structure(question):
            return brief_answer(
                "إلا كان عندك 6 شهور ديال الخدمة المتواصلة، عندك الحق فالعطلة السنوية المؤدى عنها.",
                [
                    "الحساب العادي هو نهار ونص على كل شهر خدمة.",
                    "إلا كان الأجير أقل من 18 عام، كيولي الحق جوج أيام على كل شهر.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
إلا كان عندك 6 شهور ديال الخدمة المتواصلة عند نفس المشغل، عندك الحق فالعطلة السنوية المؤدى عنها: نهار ونص ديال العمل الفعلي على كل شهر خدمة. إلا كان الأجير أقل من 18 عام، الحق هو جوج أيام ديال العمل الفعلي على كل شهر خدمة. {first_source}

الشرح:
- الحق فالعطلة السنوية كيبدا من بعد 6 شهور ديال الخدمة المتواصلة.
- الحساب العادي هو 1.5 يوم عمل فعلي على كل شهر خدمة.
- الأجير أقل من 18 سنة عندو 2 أيام عمل فعلي على كل شهر خدمة.

الأساس القانوني:
Article 231 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
حسب عدد الشهور اللي خدمتي، وراجع العقد أو الاتفاقية الجماعية إلا كانت كتعطي امتيازات أكثر.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "salary") and contains_all(
        context,
        "article 361",
        "défaut de paiement du salaire",
    ):
        first_source = citation_for_match(chunks, "article 361")
        if not should_use_full_structure(question):
            return brief_answer(
                "إلا المشغل ما خلصكش، هادشي ماشي عادي: عدم أداء الأجر مخالفة مذكورة فمدونة الشغل.",
                [
                    "الأجر خاصو يتخلص بآجال منتظمة.",
                    "احتافظ بأي دليل على الخدمة والأجر اللي ما توصّلتيش به.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
إلا المشغل ما خلصكش، فعدم أداء الأجر مخالفة مذكورة فمدونة الشغل، وماشي وضع عادي خاصك تقبلو. {first_source}

الشرح:
- المدونة كتنص على عقوبة عند عدم أداء الأجر أو أداء أجر أقل من الحد الأدنى القانوني.
- الأجر خاصو يتخلص بآجال منتظمة حسب نوع الأجير.
- فالجواب ديالك، المهم هو تجمع ما يثبت الخدمة والخلاص اللي ما توصّلتيش به.

الأساس القانوني:
Articles 361 و363 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
جمع العقد، كشوفات الأداء، الرسائل، وأي وثيقة كتبيّن الخدمة والأجر، وطلب توضيح كتابي من المشغل قبل ما تبني أي خطوة أخرى.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "paid_leave") and has_source_category(
        chunks, "code_travail"
    ):
        first_source = first_citation(chunks)
        return brief_answer(
            "إلا كان السؤال على الكونجي أو العطلة السنوية، خاص الطلب والرفض يتوثقو باش نعرفو واش المشكل فالتوقيت، الرصيد، ولا رفض غير مبرر.",
            [
                "راجع شحال خدمتي وشحال عندك من أيام العطلة حسب الوثائق المتوفرة.",
                "طلب الجواب كتابيا، وخلي نسخة من الطلب وأي رفض أو تأجيل.",
                "ما نقدرش نحسم واش الرفض قانوني بلا التواريخ ورصيد العطلة وسبب المشغل.",
            ],
            first_source,
            "عمليا، جمع العقد، كشوفات الأداء أو الحضور، طلب الكونجي، وأي رسالة فيها الرفض أو التأجيل.",
        )

    if (
        question_matches_topic(topic_question, "salary")
        and not question_matches_topic(topic_question, "overtime")
        and has_source_category(chunks, "code_travail")
    ):
        first_source = first_citation(chunks)
        return brief_answer(
            "إلا كان المشكل فالأجر، التأخير، أو اقتطاع ما مفهوماش، خاصنا نقارنو كلام المشغل مع كشف الأداء والوثائق قبل أي خلاصة.",
            [
                "الأهم هو تثبت شحال خدمتي، شحال متفق عليه، وشنو تخلصتي فعلا.",
                "فالاقتطاعات، طلب سبب مكتوب وشوف واش باين فbulletin ولا غير قرار شفوي.",
                "ما نقدرش نحدد مبلغ أو نتيجة نهائية بلا كشف الأداء والتواريخ.",
            ],
            first_source,
            "عمليا، جمع bulletin، كشوفات البنك أو الأداء، الرسائل، وجدول الأيام والساعات اللي خدمتي.",
        )

    if question_matches_topic(topic_question, "overtime") and contains_all(
        context,
        "article 201",
        "heures supplémentaires",
        "majoration de salaire",
    ):
        first_source = citation_for_match(chunks, "article 201")
        if not should_use_full_structure(question):
            return brief_answer(
                "نعم، الساعات الإضافية كتستحق زيادة فالأجر.",
                [
                    "النسبة كتختلف حسب التوقيت.",
                    "فالراحة الأسبوعية، الزيادة كتكون أكبر.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
نعم، الساعات الإضافية كتستحق زيادة فالأجر، والنسبة كتختلف حسب وقت الخدمة واش كانت فالنهار ولا فالليل ولا فنهار الراحة الأسبوعية. {first_source}

الشرح:
- Article 201 كينص على زيادة 25% أو 50% حسب التوقيت.
- إلا كانت الساعات الإضافية فنهار الراحة الأسبوعية، الزيادة كتطلع أكثر.
- ماشي أي ساعة زايدة كتتحسب بنفس الطريقة؛ خاصها تدخل فعلا فتعريف الساعات الإضافية.

الأساس القانوني:
Articles 199 إلى 202 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
سجل الأيام والساعات اللي خدمتيهم، وراجع شنو كيبان فالعقد وكشف الأداء قبل ما تناقش الحساب مع المشغل.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "overtime") and has_source_category(
        chunks, "code_travail"
    ):
        first_source = first_citation(chunks)
        return brief_answer(
            "إلا كان السؤال على heures sup أو ساعات زايدة، خاص نثبتو الساعات والتوقيت وشنو باين فbulletin قبل حساب أي تعويض.",
            [
                "فرق بين ساعات الخدمة العادية والساعات اللي تزادت بطلب أو علم المشغل.",
                "احتافظ بplanning، رسائل التكليف، وساعات الدخول والخروج.",
                "ما نقدرش نحسب مبلغ نهائي بلا عدد الساعات، التوقيت، والأجر الأساسي.",
            ],
            first_source,
            "عمليا، وجد جدول بالأيام والساعات، وقارنو مع كشف الأداء والرسائل قبل ما تطلب توضيح مكتوب.",
        )

    if question_matches_topic(topic_question, "work_certificate"):
        first_source = citation_for_match(chunks, "certificat de travail")
        if not should_use_full_structure(question):
            return brief_answer(
                "نعم، منين كيسالي عقد الشغل، المشغل خاصو يعطيك شهادة العمل داخل أجل أقصاه 8 أيام.",
                [
                    "الشهادة كتبيّن تاريخ الدخول، تاريخ الخروج، والمناصب اللي خدمتي فيها.",
                    "إلا ما تسلماتش، النص كيهضر على إمكانية التعويض عن الضرر.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
نعم، منين كيسالي عقد الشغل، المشغل خاصو يعطيك شهادة العمل داخل أجل أقصاه 8 أيام. {first_source}

الشرح:
- الشهادة خاصها تبين تاريخ الدخول، تاريخ الخروج، والمناصب اللي خدمتي فيها.
- النص كيربط تسليمها بانتهاء عقد الشغل.
- إلا ما تسلماتش، المدونة كتذكر إمكانية التعويض عن الضرر.

الأساس القانوني:
Article 72 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
طلب الشهادة كتابيا واحتافظ بنسخة من الطلب وأي جواب توصّلتي به.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "sick_leave") and contains_all(
        context,
        "article 271",
        "certificat médical",
    ):
        first_source = citation_for_match(chunks, "article 271")
        if not should_use_full_structure(question):
            return brief_answer(
                "إلا غبتي بسبب المرض، خاصك تعلم المشغل داخل 48 ساعة، وإذا طال الغياب أكثر من 4 أيام خاصك تقدم شهادة طبية.",
                [
                    "المشغل يقدر يدير فحصا مضادا على نفقته.",
                    "الأهم هو التبليغ والاحتفاظ بالدليل.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
إلا غبتي بسبب المرض، خاصك تعلم المشغل داخل 48 ساعة، وإذا طال الغياب أكثر من 4 أيام خاصك تقدم شهادة طبية كتثبت الغياب. {first_source}

الشرح:
- النص ما كيقولش إن المشغل يقدر يمنع الغياب المبرر بالمرض كيف ما جا.
- كيطلب منك التبليغ والتبرير داخل الآجال المذكورة.
- المشغل يقدر يدير فحصا مضادا على نفقته خلال مدة الغياب المحددة فالشهادة.

الأساس القانوني:
Article 271 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
بلغ المشغل بسرعة، واحتافظ بنسخة من الشهادة الطبية وأي دليل على التبليغ.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "maternity_leave") and (
        "article 159" in context or "protection de la maternité" in context
    ):
        first_source = citation_for_match(chunks, "article 159")
        return brief_answer(
            "نعم، إلا كان السؤال على الحامل أو الرجوع بعد الولادة، فمدونة الشغل كتقرر حماية خاصة مرتبطة بالحمل والأمومة. إذا كان الحمل مثبت بشهادة طبية، المشغل ما يقدرش يفسخ العقد خلال مدة الحمل ولا خلال 14 أسبوع من بعد الولادة إلا فحالات قانونية محددة جدا.",
            [
                "الحماية هنا ماشي طرد عادي؛ خاص التركيز يكون على الحمل، الشهادة الطبية، وتاريخ الولادة.",
                "كاين حق فعطلة أمومة مدتها 14 أسبوع على الأقل حسب السياق المسترجع.",
                "أي قرار ديال الفصل خاصو يتقرا بحذر: واش السبب مستقل فعلا على الحمل، وواش كاينة وثائق كتثبتو.",
                "إلا كان الرفض بعد الولادة، مهم نشوفو تاريخ الرجوع، المراسلات، وشنو السبب اللي عطاه المشغل.",
            ],
            first_source,
            "احتافظي بالشهادة الطبية، إشعار الحمل أو الولادة، أي قرار مكتوب من المشغل، وكامل الرسائل اللي كتهضر على الرجوع للخدمة.",
        )

    if (
        question_matches_topic(topic_question, "termination")
        and ("بلا سبب" in question or "بدون سبب" in question)
        and "licenciement" in context
        and "34" in source_pages(chunks)
    ):
        first_source = next(
            chunk.citation for chunk in chunks if chunk.page == "34"
        )
        if not should_use_full_structure(question):
            return brief_answer(
                "لا، الطرد خاصو يكون مبني على سبب واضح ومقبول قانونيا، وماشي مجرد قرار بلا تعليل.",
                [
                    "حتى فحالة الخطأ الجسيم، خاص الأجير يتسمع ليه قبل الفصل.",
                    "إلا ما تحترماتش المسطرة، يقدر يطرح مشكل قانوني.",
                ],
                first_source,
                "عمليا، جمع رسالة الطرد، العقد، ومحضر الاستماع إلا كان.",
            )
        return f"""
الجواب المختصر:
إلا تطردتي بلا سبب واضح ومقبول، ما خاصش يتقدم الطرد كأنه إجراء عادي بلا تعليل، وخص المشغل يحترم المسطرة القانونية ديال الفصل. {first_source}

الشرح:
- فحالة الخطأ الجسيم كاين نظام خاص، ولكن حتى قبل الفصل خاص الأجير يتسمع ليه ويدافع على راسو.
- النصوص اللي فالسياق كتبرز أن الفصل ماشي مجرد قرار شفوي بلا مسطرة.
- التعويضات والنتيجة النهائية كيبقاو مرتبطين بالوقائع والوثائق، لذلك ما يمكنش نعطيك ضمانة نهائية من غير ملف كامل.

الأساس القانوني:
Articles 61 و62 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
احتافظ برسالة الطرد إن وجدت، محضر الاستماع، وأي مراسلة مرتبطة بالسبب المذكور، وقارنها مع الوقائع الحقيقية.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if (
        question_matches_topic(topic_question, "termination")
        and "34" in source_pages(chunks)
    ):
        first_source = next(
            chunk.citation for chunk in chunks if chunk.page == "34"
        )
        return brief_answer(
            "إلا قالو ليك ما تبقاش تجي أو منعوك ترجع للخدمة، خاصنا نشوفو السبب والمسطرات قبل أي خلاصة.",
            [
                "قرار الفصل خاصو يذكر الأسباب، وكيبان فالسياق أن الاستماع والمحضر مهمين فمسطرة الفصل.",
                "ما نقدرش نأكد واش الطرد قانوني أو لا بلا وثائق الحالة.",
            ],
            first_source,
            "عمليا، جمع رسالة الطرد، محضر الاستماع، العقد، وكشوفات الأداء.",
        )

    if question_matches_topic(topic_question, "preavis") and contains_all(
        context,
        "article 51",
        "indemnité de préavis",
    ):
        first_source = citation_for_match(chunks, "article 51")
        if not should_use_full_structure(question):
            return brief_answer(
                "الـ préavis هو مهلة الإخطار قبل إنهاء عقد الشغل غير محدد المدة.",
                [
                    "إلا ما تحترمش بلا خطأ جسيم، كيكون ممكن تعويض بدل هاد المهلة.",
                    "المدة كتبدل حسب الحالة والنصوص المنظمة.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
الـ préavis هو مهلة الإخطار قبل إنهاء عقد الشغل غير محدد المدة، وإذا ما تحترمش بلا خطأ جسيم، كيكون ممكن تعويض بدل هاد المهلة. {first_source}

الشرح:
- Article 51 كيربط عدم احترام مهلة الإخطار بتعويض يعادل الأجر اللي كان غادي يتخلص خلال المهلة.
- فالخطأ الجسيم، كاين استثناء مهم منصوص عليه فمدونة الشغل.
- المدة نفسها كتبدل حسب الحالة والنصوص المنظمة.

الأساس القانوني:
Article 51 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
شوف واش العقد ديالك CDI، واش كاين إشعار مكتوب، وشنو السبب المذكور لإنهاء العلاقة.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "resignation"):
        first_source = citation_for_match(chunks, "article 51")
        return brief_answer(
            "إلا كان السؤال على الاستقالة، تعامل معها بحذر وخلي كلشي مكتوب وواضح، خصوصا إلا كان كاين ضغط من المشغل أو ندم من بعد التوقيع.",
            [
                "ما نقدرش نأكد واش استقالة معينة صحيحة أو لا بلا نشوفو شنو تكتب، واش كان ضغط، وشنو وقع من بعد.",
                "إلا كان العقد CDI، راجع واش كاين préavis أو أثر مالي مرتبط بإنهاء العلاقة.",
                "إلا قالو ليك وقع باش تاخذ فلوسك، ما توقع حتى تفهم الوثيقة وتحتافظ بنسخة منها.",
            ],
            first_source,
            "عمليا، جمع الواتسابات، نسخة الاستقالة إن وجدت، كشوفات الأداء، وكتب ملخص بالتواريخ قبل أي خطوة.",
        )

    if question_matches_topic(topic_question, "contract") and contains_all(
        context,
        "article 16",
        "durée déterminée",
        "durée indéterminée",
    ):
        first_source = citation_for_match(chunks, "article 16")
        if not should_use_full_structure(question):
            return brief_answer(
                "CDD هو عقد لمدة محددة، وCDI هو عقد لمدة غير محددة.",
                [
                    "CDD كيتستعمل غير فحالات معينة بحال التعويض المؤقت أو العمل الموسمي.",
                    "الاسم بوحدو ما يكفيش؛ المهم واش الحالة كتوافق النص.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
CDD هو عقد لمدة محددة، وCDI هو عقد لمدة غير محددة. ومدونة الشغل كتخلي CDD للحالات اللي العلاقة فيها ما يمكنش تكون مستمرة بطبيعتها. {first_source}

الشرح:
- CDD كيتستعمل مثلا للتعويض المؤقت، الزيادة المؤقتة فالنشاط، أو العمل الموسمي.
- CDI ما عندوش تاريخ نهاية محدد من البداية.
- اختيار النوع ماشي غير بالاسم؛ خاصو يوافق الحالة القانونية ديال الشغل.

الأساس القانوني:
Article 16 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
راجع واش العقد ديالك فيه مدة محددة وشنو السبب المذكور لها، وقارن هاد السبب مع الحالات اللي كيعترف بها النص.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "maternity_leave") and (
        "article 159" in context or "protection de la maternité" in context
    ):
        first_source = citation_for_match(chunks, "article 159")
        if not should_use_full_structure(question):
            return brief_answer(
                "نعم، المرأة الحامل عندها حماية خاصة فمدونة الشغل.",
                [
                    "إلا كان الحمل مثبت بشهادة طبية، المشغل ما يقدرش يفسخ العقد خلال الحمل ولا خلال 14 أسبوع من بعد الولادة إلا فحالات محددة.",
                    "كاين كذلك حق فعطلة أمومة مدتها 14 أسبوع على الأقل.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
نعم، المرأة الحامل عندها حماية خاصة فمدونة الشغل. إلا كان الحمل مثبت بشهادة طبية، المشغل ما يقدرش يفسخ العقد خلال مدة الحمل ولا خلال 14 أسبوع من بعد الولادة، إلا فحالات قانونية محددة جدا. {first_source}

الشرح:
- كاين حق فعطلة أمومة مدتها 14 أسبوع على الأقل.
- كاينة حماية من إنهاء العقد أثناء الحمل وبعد الولادة.
- النص كيسمح باستثناءات محدودة، لذلك خاص كل حالة تتقرا حسب الوثائق والسبب المذكور.

الأساس القانوني:
Articles 152 و159 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
احتافظي بالشهادة الطبية وبأي مراسلة من المشغل، وراجعي واش أي قرار مكتوب احترم هاد الحماية القانونية.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "notice_job_search") and contains_all(
        context,
        "article 48",
        "recherche d'un autre emploi",
    ):
        first_source = citation_for_match(chunks, "article 48")
        if not should_use_full_structure(question):
            return brief_answer(
                "نعم، خلال مدة الإخطار عندك الحق فغيابات مؤدى عنها باش تقلب على خدمة أخرى.",
                [
                    "الحق كيتنظم بساعتين فالنهار مع حدود أسبوعية وشهرية.",
                    "كيوقف إلا لقيتي خدمة جديدة أو ما بقيتيش كتستعمل الغياب لهاد الغرض.",
                ],
                first_source,
            )
        return f"""
الجواب المختصر:
نعم، خلال مدة الإخطار عندك الحق فغيابات مؤدى عنها باش تقلب على خدمة أخرى، بشرط تستعملها فعلا لهذا الغرض. {first_source}

الشرح:
- Article 48 كيعطي هاد الحق خلال مدة الإخطار.
- Article 49 كينظم المدة: ساعتين فالنهار، مع حدود أسبوعية وشهرية.
- الحق كيسالي إلا لقيتي خدمة جديدة أو ما بقيتيش كتستعمل الغياب للبحث عن عمل.

الأساس القانوني:
Articles 48 إلى 50 من مدونة الشغل. {first_source}

شنو يدير المستخدم:
نسق الغيابات مع المشغل واحتافظ بأي اتفاق أو مراسلة على التوقيت.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    if question_matches_topic(topic_question, "labor_inspection") and has_source_category(
        chunks, "labor_inspection"
    ):
        first_source = next(
            chunk.citation for chunk in chunks if chunk_has_category(chunk, "labor_inspection")
        )
        return brief_answer(
            "إلى بغيتي تمشي لمفتشية الشغل، ركز على عرض الوقائع والوثائق بشكل واضح ومهني، وخلي الشكاية مرتبطة بمشكل الشغل المحدد.",
            [
                "مفتشية الشغل كتعاون فالتواصل، التوجيه، ومحاولة تسوية بعض نزاعات الشغل حسب المعطيات المتوفرة.",
                "خاصك توضّح شكون المشغل، نوع المشكل، التواريخ، وشنو طلبتي من الشركة قبل ذلك.",
                "ما تعطيش وعود أو اتهامات بلا دليل؛ خليك فالأحداث والوثائق.",
            ],
            first_source,
            "عمليا، حضر العقد أو أي دليل على الخدمة، كشوفات الأجر، الرسائل، وأي قرار مكتوب، ودير ملخص قصير بالترتيب الزمني.",
        )

    return None


def format_context(chunks: list[SourceChunk]) -> str:
    return "\n\n---\n\n".join(
        (
            f"Source {chunk.number} - category={chunk.category}, "
            f"file={chunk.source}, page={chunk.page}:\n{chunk.text}"
        )
        for chunk in chunks
    )


def combine_query_parts(*parts: str) -> str:
    seen = set()
    unique_parts = []
    for part in parts:
        clean_part = (part or "").strip()
        if not clean_part or clean_part in seen:
            continue
        seen.add(clean_part)
        unique_parts.append(clean_part)
    return " ".join(unique_parts)


def intent_names_compatible(left: str, right: str) -> bool:
    if not left or not right or left == right:
        return True
    groups = (
        {"dismissal", "dismissal_unclear", "abusive_dismissal", "disciplinary_dismissal"},
        {"contract", "contract_cdd_cdi", "no_written_contract"},
        {"cnss", "cnss_non_declaration"},
        {"work_accident", "work_accident_compensation"},
        {"maternity", "maternity_protection"},
        {"salary_unpaid", "salary_deduction"},
        {"paid_leave", "annual_leave"},
    )
    return any(left in group and right in group for group in groups)


def format_analysis_for_prompt(analysis: dict | None) -> str:
    if not analysis:
        return "غير متوفر."

    prompt_analysis = {
        "intent": analysis.get("intent"),
        "facts": analysis.get("facts", {}),
        "legal_issues": analysis.get("legal_issues", []),
        "needs_clarification": analysis.get("needs_clarification", False),
        "clarification_question": analysis.get("clarification_question"),
        "confidence": analysis.get("confidence"),
    }
    return json.dumps(prompt_analysis, ensure_ascii=False, indent=2)


def search_law(question: str, n_results: int = N_RESULTS):
    return format_context(retrieve_law(question, n_results=n_results))


def build_messages(
    question: str,
    context: str,
    uncertainty_prefix: str = "",
    legal_confidence: str = "high",
    analysis: dict | None = None,
):
    analysis_context = format_analysis_for_prompt(analysis)
    answer_shape = """
استعمل هذا الشكل فكل جواب قانوني:

فهمت الحالة:
فسر باختصار شنو باين من سؤال المستخدم بلا ما تفترض وقائع ما قالهاش.

الجواب القانوني:
عطي الجواب القانوني مع الشروط والاستثناءات المهمة.

شنو مهم تعرف:
- 3 حتى 5 نقط قانونية أو عملية مهمة.

شنو تدير دابا:
- 3 حتى 5 خطوات عملية.

المصادر:
ذكر الاستشهادات بصيغة: [المصدر 1، الصفحة 34]

تنبيه:
هاد الجواب للتوجيه فقط وماشي استشارة قانونية رسمية.

الطول:
- سؤال قانوني بسيط: 120 حتى 180 كلمة.
- سؤال قانوني معقد: 180 حتى 300 كلمة.
"""
    system_prompt = f"""
أنت مساعد قانوني مهني مختص فقط فمدونة الشغل المغربية، وماشي محامي وما كتقدمش ضمانات نهائية.

القواعد:
- جاوب غير بالدارجة المغربية وبأسلوب بسيط، مهني، وطبيعي.
- خليك واضح ومفيد، بلا عبارات روبوتية وبلا خلط لغات.
- ما تقولش أنك محامي، وما تعطي حتى ضمانة نهائية أو نتيجة مؤكدة.
- جاوب غير انطلاقا من السياق القانوني اللي عطيتك، وما تستعملش المعرفة العامة.
- استعمل تحليل الحالة باش تفهم الوقائع، ولكن إلا كان شي fact قيمتو unknown ما تفترضوش.
- legal_issues كتعاونك تختار الزاوية القانونية، ولكن الحكم النهائي خاصو يبقى مربوط بالمصادر المسترجعة.
- أي حكم قانوني خاصو يكون مربوط بالمصدر اللي بان فالسياق.
- ما تخترعش مواد، آجال، إجراءات، مؤسسات، ولا خلاصات ما كايناش فالسياق.
- درجة الثقة فاكتمال الوقائع: {legal_confidence}.
- إلا كانت درجة الثقة low أو medium، بدا الجواب بصياغة شرطية وما تفترضش أن المستخدم تطرد أو دار خطأ جسيم.
- تجنب عبارات حاسمة بحال "تم فصلك"، "أنت مطرود"، و"فالخطأ الجسيم" إلا إذا المستخدم قال هاد الوقائع بوضوح أو المصدر والسياق كيدعموها مباشرة.
- إذا كان هذا التنبيه غير فارغ، استعمل معناه فبداية الجواب: {uncertainty_prefix}
- إلا كان السياق ضعيف، ناقص، أو ما كيجاوبش مباشرة على السؤال، قل بالضبط:
  "{INSUFFICIENT_CONTEXT_MESSAGE}"
- كل جواب قانوني خاصو يذكر مصدر واحد على الأقل بصيغة: [المصدر 1، الصفحة 34]
- ما تستعملش الإنجليزية ولا الصينية ولا الفرنسية فالشرح، إلا فاسم قانوني موجود فالمصدر بحالو.
{answer_shape}
"""

    user_prompt = f"""
السؤال ديال المستخدم:
{question}

تحليل الحالة قبل البحث:
{analysis_context}

السياق القانوني المستخرج من المصادر القانونية:
{context}
"""

    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]


def context_is_sufficient(question: str, chunks: list[SourceChunk]) -> bool:
    """Refuse early when retrieval lacks enough legal support."""
    if not chunks:
        return False

    expanded_question = expand_query(question)
    return any(
        keyword_score(chunk.text, expanded_question) >= MIN_RELEVANCE_SCORE
        or anchor_score(chunk.text, expanded_question) > 0
        for chunk in chunks
    )


def contains_unrelated_language(answer: str) -> bool:
    # Guard against clearly unrelated script/language drift in model outputs.
    if re.search(r"[\u4e00-\u9fff]", answer):
        return True

    english_markers = ("here is", "as an ai", "based on the context")
    return any(marker in answer.lower() for marker in english_markers)


def has_unsupported_unsafe_phrase(answer: str) -> bool:
    if any(phrase in answer for phrase in UNSAFE_PHRASES):
        return True
    return any(phrase in answer for phrase in UNSUPPORTED_ACTION_PHRASES)


def has_invented_article(question: str, answer: str, chunks: list[SourceChunk]) -> bool:
    """Reject article numbers that were not present in the retrieved legal text."""
    context = "\n".join(chunk.text for chunk in chunks)
    allowed_articles = set(ARTICLE_PATTERN.findall(context))
    asked_article = asks_for_specific_article(question)

    for article in ARTICLE_PATTERN.findall(answer):
        if article == asked_article:
            continue
        if article not in allowed_articles:
            return True
    return False


def contradicts_question_intent(question: str, answer: str, chunks: list[SourceChunk]) -> bool:
    normalized_question = question.lower()
    normalized_answer = answer.lower()
    context = "\n".join(chunk.text for chunk in chunks).lower()

    if question_matches_topic(question, "salary"):
        salary_due = "défaut de paiement du salaire" in context or "article 363" in context
        says_not_due = "ما خاصوش يخلص" in normalized_answer or "ما عليهش يخلص" in normalized_answer
        if salary_due and says_not_due:
            return True

    if question_matches_topic(question, "overtime"):
        overtime_paid = "article 201" in context and "majoration de salaire" in context
        says_unpaid = "ما خاصهاش تخلص" in normalized_answer or "ما تتخلصش" in normalized_answer
        if overtime_paid and says_unpaid:
            return True

    return False


def should_attach_sources(answer_type: str, sources: list[SourceChunk]) -> bool:
    """Citations are only mandatory for legal answers backed by retrieved sources."""
    return answer_type in {"legal_rag", "verified_rule"} and bool(sources)


def answer_is_valid(
    question: str,
    answer: str,
    chunks: list[SourceChunk],
    answer_type: str = "legal_rag",
) -> bool:
    """Validate generated answers before exposing them to the user."""
    if not answer.strip():
        return False
    if len(answer) > MAX_GENERATED_ANSWER_CHARS:
        return False
    if should_attach_sources(answer_type, chunks) and not CITATION_PATTERN.search(answer):
        return False
    if contains_unrelated_language(answer):
        return False
    if has_unsupported_unsafe_phrase(answer):
        return False
    if has_invented_article(question, answer, chunks):
        return False
    if contradicts_question_intent(question, answer, chunks):
        return False
    return True


def ask_chatbot(question: str, n_results: int = N_RESULTS, return_sources: bool = False):
    """Answer from Moroccan labor-law sources, refusing when support is weak."""
    conversation_classification = classify_conversation(question)
    if conversation_classification["type"] != "labor_law":
        answer = normal_darija_response(question, conversation_classification)
        return (answer, []) if return_sources else answer

    intent_result = detect_darija_intent(question)
    analysis = analyze_question(question) if USE_LEGAL_UNDERSTANDING else None
    direct_answer = direct_answer_for_intent(intent_result.intent)
    is_clear_unclear_turn = (
        intent_result.intent == "unclear"
        and (
            intent_result.matched_by in {"exact", "empty"}
            or len(normalize_conversation_text(question).split()) <= 3
        )
    )
    if (
        direct_answer
        and should_treat_as_native_direct_answer(question, intent_result)
        and (intent_result.intent != "unclear" or is_clear_unclear_turn)
    ):
        return (direct_answer, []) if return_sources else direct_answer

    conversational_answer = conversation_router(question)
    if conversational_answer:
        return (conversational_answer, []) if return_sources else conversational_answer

    if asks_for_legal_guarantee(question):
        answer = legal_guarantee_refusal_answer()
        return (answer, []) if return_sources else answer

    if is_obviously_out_of_scope(question):
        answer = refusal_answer()
        return (answer, []) if return_sources else answer

    analysis_query = ""
    if analysis:
        analysis_query = str(analysis.get("search_query") or "").strip()
    analysis_intent = str(analysis.get("intent") or "") if isinstance(analysis, dict) else ""
    detector_query = ""
    if (
        intent_result.is_legal
        and intent_result.normalized_query
        and intent_names_compatible(analysis_intent, intent_result.intent)
    ):
        detector_query = intent_result.normalized_query

    if USE_LEGAL_UNDERSTANDING and analysis_query:
        expanded_query = combine_query_parts(
            question,
            analysis_query,
            detector_query,
        )
    elif intent_result.is_legal and intent_result.normalized_query:
        expanded_query = f"{question} {intent_result.normalized_query}"
    elif has_legal_context_in_conversation(question):
        expanded_query = expand_query(question)
    else:
        expanded_query = question
    answer_intent = intent_result
    if analysis_intent and analysis_intent not in {"unclear", "out_of_scope"}:
        answer_intent = SimpleNamespace(
            intent=analysis_intent,
            confidence=float(analysis.get("confidence", intent_result.confidence))
            if isinstance(analysis, dict)
            else intent_result.confidence,
        )
    uncertainty_prefix, legal_confidence = build_uncertainty_prefix(question, answer_intent)

    if RAG_DEBUG:
        print("Conversation classification:", conversation_classification)
        print("Intent:", intent_result)
        print("Analysis:", analysis)
        print("Expanded:", expanded_query)
        print("Legal confidence:", legal_confidence)

    chunks = retrieve_law(expanded_query, n_results=n_results)

    article_number = asks_for_specific_article(expanded_query)
    if article_number and not context_has_article(article_number, chunks):
        answer = refusal_answer()
        return (answer, []) if return_sources else answer

    if not context_is_sufficient(expanded_query, chunks):
        answer = refusal_answer()
        return (answer, []) if return_sources else answer

    if USE_VERIFIED_RULES_FIRST:
        verified_answer = answer_from_verified_rules(expanded_query, chunks, question)
    else:
        verified_answer = None
    if verified_answer:
        chunks = verified_source_subset(question, chunks)
        verified_answer = soften_uncertain_answer(verified_answer, question, legal_confidence)
        verified_answer = apply_uncertainty_prefix(verified_answer, uncertainty_prefix)
        return (verified_answer, chunks) if return_sources else verified_answer

    context = format_context(chunks)
    messages = build_messages(question, context, uncertainty_prefix, legal_confidence, analysis)

    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json={
                "model": CHAT_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.25,
                    "top_p": 0.8,
                    "num_ctx": 4096,
                    "num_predict": CHAT_NUM_PREDICT,
                    "repeat_penalty": 1.12,
                    "num_thread": 8,
                },
            },
            timeout=300,
        )
        response.raise_for_status()
        answer = response.json()["message"]["content"].strip()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        fallback_answer = answer_from_verified_rules(expanded_query, chunks, question)
        if fallback_answer:
            fallback_chunks = verified_source_subset(question, chunks)
            fallback_answer = soften_uncertain_answer(
                fallback_answer,
                question,
                legal_confidence,
            )
            fallback_answer = apply_uncertainty_prefix(fallback_answer, uncertainty_prefix)
            return (fallback_answer, fallback_chunks) if return_sources else fallback_answer
        raise
    except requests.exceptions.RequestException as exc:
        fallback_answer = answer_from_verified_rules(expanded_query, chunks, question)
        if fallback_answer:
            fallback_chunks = verified_source_subset(question, chunks)
            fallback_answer = soften_uncertain_answer(
                fallback_answer,
                question,
                legal_confidence,
            )
            fallback_answer = apply_uncertainty_prefix(fallback_answer, uncertainty_prefix)
            return (fallback_answer, fallback_chunks) if return_sources else fallback_answer
        error_text = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
        raise RuntimeError(
            f"Ollama chat failed for model '{CHAT_MODEL}': {error_text.strip()}"
        ) from exc

    if should_attach_sources("legal_rag", chunks) and not CITATION_PATTERN.search(answer):
        citations = " ".join(chunk.citation for chunk in chunks[: min(2, len(chunks))])
        answer = f"{answer.rstrip()}\n\nالمصادر: {citations}"

    answer = soften_uncertain_answer(answer, question, legal_confidence)
    answer = apply_uncertainty_prefix(answer, uncertainty_prefix)

    if not answer_is_valid(expanded_query, answer, chunks, "legal_rag"):
        fallback_answer = answer_from_verified_rules(expanded_query, chunks, question)
        if fallback_answer:
            fallback_chunks = verified_source_subset(question, chunks)
            fallback_answer = soften_uncertain_answer(
                fallback_answer,
                question,
                legal_confidence,
            )
            fallback_answer = apply_uncertainty_prefix(fallback_answer, uncertainty_prefix)
            return (fallback_answer, fallback_chunks) if return_sources else fallback_answer
        answer = refusal_answer()
        chunks = []

    return (answer, chunks) if return_sources else answer


def print_sources(chunks: list[SourceChunk]):
    print("\nSources retrieved:")
    for chunk in chunks:
        distance = "" if chunk.distance is None else f", distance={chunk.distance:.4f}"
        print(
            f"- source {chunk.number}: category={chunk.category}, "
            f"file={chunk.source}, page={chunk.page}{distance}"
        )


if __name__ == "__main__":
    print("\n=== CHATBOT QANON CHOGHL - LOCAL OLLAMA ===")
    terminal_print("كتب السؤال ديالك. للخروج كتب: exit\n")

    while True:
        question = input("Sawal dyalek: ").strip()

        if question.lower() in ["exit", "quit", "q"]:
            terminal_print("تم الخروج.")
            break

        if not question:
            continue

        try:
            if conversation_router(question) is None:
                terminal_print("خود لحظة، غادي نقلب ليك فالمصدر القانوني...")
            answer, sources = ask_chatbot(question, return_sources=True)

            print("=" * 50)
            terminal_print(answer)
            print("=" * 50)
            print_sources(sources)
            print()

        except chromadb.errors.NotFoundError:
            terminal_print("\nERROR: قاعدة المعرفة ما لقاهاش.")
            terminal_print("خاصك تشغل أولا:")
            print("python ingest.py\n")

        except requests.exceptions.ConnectionError:
            terminal_print("\nERROR: Ollama ما خدامش.")
            terminal_print("شغل هاد الأمر ف terminal آخر:")
            print("ollama serve\n")

        except requests.exceptions.Timeout:
            terminal_print("\nERROR: الموديل طول بزاف.")
            terminal_print("جرب موديل أصغر أو نقص RAG_N_RESULTS.\n")

        except Exception as e:
            print(f"\nERROR: {e}\n")
