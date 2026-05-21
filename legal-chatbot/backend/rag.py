import os
import re
import sys
from dataclasses import dataclass

import chromadb
import requests

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "code_travail_maroc"

OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")

EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b")
N_RESULTS = int(os.getenv("RAG_N_RESULTS", "2"))
MAX_GENERATED_ANSWER_CHARS = int(os.getenv("RAG_MAX_ANSWER_CHARS", "1800"))
MIN_RELEVANCE_SCORE = int(os.getenv("RAG_MIN_RELEVANCE_SCORE", "4"))

INSUFFICIENT_CONTEXT_MESSAGE = (
    "ما لقيتش جواب قانوني كافي فالمصدر المتوفر. "
    "هاد المساعد محدود فمدونة الشغل المغربية."
)

LEGAL_TOPIC_TERMS = {
    "preavis": [
        "préavis", "preavis", "délai de préavis", "delai de preavis",
        "إنذار", "انذار", "إشعار", "اشعار", "مدة الإخطار",
        "مدة الإنذار", "تعويض الإخطار", "indemnité de préavis",
    ],
    "salary": [
        "الأجر", "اجر", "أجرة", "الصالير", "السالير", "خلصني",
        "ما خلصنيش", "ما تخلصتش", "الخلاص", "عدم أداء الأجر",
        "أجر غير مؤدى", "salaire", "rémunération", "remuneration",
        "paiement du salaire", "défaut de paiement du salaire",
    ],
    "overtime": [
        "الساعات الإضافية", "ساعات إضافية", "ساعة إضافية",
        "السوايع الزايدة", "heures supplémentaires",
        "heures supplementaires", "majoration de salaire",
    ],
    "sick_leave": [
        "مرض", "المرض", "مريض", "طبيب", "شهادة طبية",
        "غياب بسبب المرض", "رخصة مرضية", "maladie", "absence pour maladie",
        "certificat médical", "certificat medical",
    ],
    "termination": [
        "طرد", "فصل", "خروج", "بلا سبب", "سبب مقبول",
        "licenciement", "indemnité de licenciement",
        "dommages-intérêts", "تعويض", "الفصل",
    ],
    "work_certificate": [
        "شهادة العمل", "شهادة الشغل", "certificat de travail",
    ],
    "disciplinary_procedure": [
        "مسطرة تأديبية", "الاستماع", "محضر الاستماع", "مسطرة الفصل",
        "procédure disciplinaire", "procedure disciplinaire",
        "être entendu", "proces-verbal", "procès-verbal",
    ],
    "gross_misconduct": [
        "خطأ جسيم", "faute grave", "بدون تعويض", "sans préavis",
    ],
    "paid_leave": [
        "كونجي", "عطلة", "إجازة", "اجازة", "سنوي",
        "العطلة السنوية", "congé annuel payé", "conge annuel paye",
        "jour et demi", "Article 231",
    ],
    "contract": [
        "CDD", "CDI", "عقد", "العقد", "contrat", "durée déterminée",
        "durée indéterminée", "contrat à durée déterminée",
        "contrat a duree determinee", "contrat à durée indéterminée",
        "contrat a duree indeterminee",
    ],
    "maternity_leave": [
        "حمل", "المرأة الحامل", "الولادة", "عطلة الولادة",
        "الحامل", "حماية الحامل", "حقوق المرأة الحامل",
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
        "مفتش الشغل", "تفتيش الشغل", "النزاعات",
        "inspecteur du travail", "inspection du travail",
    ],
    "cnss": [
        "cnss", "الضمان الاجتماعي", "تصريح", "التصريح",
        "caisse nationale de sécurité sociale",
    ],
}

TOPIC_ANCHORS = {
    "preavis": ("article 51", "indemnité de préavis"),
    "salary": ("article 361", "défaut de paiement du salaire", "article 363"),
    "overtime": ("article 201", "heures supplémentaires", "majoration de salaire"),
    "sick_leave": ("article 271", "certificat médical"),
    "termination": ("article 63", "motif acceptable", "justification du licenciement"),
    "work_certificate": ("article 72", "certificat de travail"),
    "paid_leave": ("article 231", "congé annuel payé"),
    "contract": ("article 16", "durée déterminée", "durée indéterminée"),
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
}

OUT_OF_SCOPE_TERMS = [
    "حادثة سير", "حادتة سير", "الطريق العام", "code de la route",
    "طلاق", "كراء", "كريت", "مول الدار", "تجارية", "تجاري", "دعوى تجارية"
]

WORK_RELATED_TERMS = [
    "خدمة", "الشغل", "العمل", "عامل", "أجير", "اجير",
    "employeur", "salarié", "travail"
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
    distance: float | None = None

    @property
    def citation(self) -> str:
        return f"[المصدر {self.number}، الصفحة {self.page}]"


def terminal_text(text: str):
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
    has_out_scope = any(term in normalized for term in OUT_OF_SCOPE_TERMS)
    has_work_term = any(term in normalized for term in WORK_RELATED_TERMS)
    return has_out_scope and not has_work_term


def asks_for_specific_article(question: str) -> str | None:
    match = re.search(r"(?:المادة|article)\s*(\d+)", question.lower())
    if not match:
        return None
    return match.group(1)


def question_matches_topic(question: str, topic: str) -> bool:
    normalized = question.lower()
    return any(term.lower() in normalized for term in LEGAL_TOPIC_TERMS[topic])


def matched_topics(question: str) -> list[str]:
    return [
        topic
        for topic in LEGAL_TOPIC_TERMS
        if question_matches_topic(question, topic)
    ]


def expand_legal_query(question: str) -> str:
    normalized = question.lower()
    expansions = []

    for terms in LEGAL_TOPIC_TERMS.values():
        if any(term.lower() in normalized for term in terms):
            expansions.extend(terms)

    if not expansions:
        return question

    unique_expansions = list(dict.fromkeys(expansions))
    return f"{question}\nFrench legal keywords: {'; '.join(unique_expansions)}"


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
    """Keep the strongest chunk per page so returned sources stay useful."""
    best_by_page = {}
    for chunk in chunks:
        current = best_by_page.get(chunk.page)
        if current is None:
            best_by_page[chunk.page] = chunk
            continue

        current_distance = float("inf") if current.distance is None else current.distance
        next_distance = float("inf") if chunk.distance is None else chunk.distance
        if next_distance < current_distance:
            best_by_page[chunk.page] = chunk

    return list(best_by_page.values())


def relevant_chunks(question: str, chunks: list[SourceChunk]) -> list[SourceChunk]:
    """Keep chunks supported by direct overlap or by a matched legal-topic anchor."""
    return [
        chunk
        for chunk in chunks
        if keyword_score(chunk.text, question) >= MIN_RELEVANCE_SCORE
        or anchor_score(chunk.text, question) > 0
    ]


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
            SourceChunk(
                number=len(chunks) + 1,
                page=str(meta.get("page", "unknown")),
                text=clean_doc,
                distance=None,
            )
        )
        seen_text.add(clean_doc)

    return chunks


def retrieve_law(question: str, n_results: int = N_RESULTS) -> list[SourceChunk]:
    """Combine vector search and keyword search, then keep useful unique sources."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = get_embedding(expand_legal_query(question))

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
        clean_doc = doc.strip().replace("\n\n", "\n")
        distance = distances[index - 1] if index - 1 < len(distances) else None

        chunks.append(
            SourceChunk(
                number=index,
                page=str(meta.get("page", "unknown")),
                text=clean_doc,
                distance=distance,
            )
        )

    chunks = add_keyword_results(collection, question, chunks)
    chunks = dedupe_chunks_by_page(chunks)

    chunks.sort(
        key=lambda chunk: (
            anchor_score(chunk.text, question) + keyword_score(chunk.text, question),
            0 if chunk.distance is None else -chunk.distance,
        ),
        reverse=True,
    )

    selected = relevant_chunks(question, chunks)[:n_results]
    return [
        SourceChunk(
            number=index,
            page=chunk.page,
            text=chunk.text,
            distance=chunk.distance,
        )
        for index, chunk in enumerate(selected, start=1)
    ]


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


def normalize_conversation_text(text: str) -> str:
    return re.sub(r"[^\w\u0600-\u06FF]+", " ", text.lower()).strip()


def conversation_router(question: str) -> str | None:
    """Handle lightweight chat turns without invoking retrieval or the LLM."""
    normalized = normalize_conversation_text(question)
    if not normalized:
        return None

    greetings = {"hi", "hello", "salam", "سلام", "السلام", "السلام عليكم", "bonjour"}
    thanks = {"شكرا", "شكراً", "merci", "thanks", "thank you"}
    goodbyes = {"bye", "باي", "مع السلامة", "إلى اللقاء", "الى اللقاء"}
    identities = {"شكون نتا", "شكون انت", "من انت", "who are you"}
    capabilities = {"شنو تقدر دير", "اش تقدر دير", "what can you do"}
    unclear_short = {"ok", "واش", "شنو"}

    if normalized in greetings:
        return (
            "سلام، مرحبا بيك. سولني على أي حاجة متعلقة بقانون الشغل المغربي: "
            "الطرد، العقد، الأجر، العطلة، CNSS، أو التعويضات."
        )

    if normalized in thanks:
        return (
            "العفو. إلا بغيتي تسول على شي حالة فالشغل، عطيني التفاصيل "
            "ونعاونك بالمعلومة القانونية المتوفرة."
        )

    if normalized in goodbyes:
        return "مع السلامة. إلا احتجتي شي معلومة على قانون الشغل، رجع سولني."

    if normalized in identities or (
        "شكون" in normalized and ("نتا" in normalized or "انت" in normalized)
    ):
        return (
            "أنا مساعد قانوني ذكي مخصص لمدونة الشغل المغربية. كنعاونك تفهم "
            "حقوقك وواجباتك، ولكن ماشي محامي وما كنقدمش استشارة قانونية رسمية."
        )

    if normalized in capabilities or (
        "تقدر" in normalized and "دير" in normalized and "شنو" in normalized
    ):
        return (
            "نقدر نشرح ليك مواضيع فمدونة الشغل بحال الطرد، العقد، الأجر، "
            "الساعات الإضافية، العطلة، شهادة العمل، وغياب المرض. "
            "ونحاول نعطيك المصدر القانوني إلا كان متوفر."
        )

    if normalized in unclear_short:
        return (
            "مرحبا، كتب ليا سؤالك بشوية ديال التفاصيل باش نقدر نعاونك مزيان "
            "فموضوع متعلق بالشغل."
        )

    return None


def should_use_full_structure(question: str) -> bool:
    """Use the longer layout only when the question needs several legal steps."""
    normalized = question.lower()
    complex_markers = (
        "كيفاش",
        "شنو ندير",
        "شنو الحقوق",
        "شنو خاص",
        "الفرق بين",
        "يتحسب",
        "المسطرة",
        "الوثائق",
        "تعويض",
        "articles",
        "المادة",
    )
    return any(marker in normalized for marker in complex_markers)


def brief_answer(
    direct_answer: str,
    points: list[str],
    citation: str,
    practical_note: str | None = None,
) -> str:
    """Build a concise conversational answer for simple questions."""
    parts = [direct_answer.strip()]
    if points:
        parts.append("\n".join(f"- {point}" for point in points))
    if practical_note:
        parts.append(practical_note.strip())
    parts.append(f"المصدر: {citation}")
    parts.append("تنبيه: هاد الجواب للتوجيه فقط وماشي استشارة قانونية رسمية.")
    return "\n\n".join(parts)


def source_pages(chunks: list[SourceChunk]) -> set[str]:
    return {chunk.page for chunk in chunks}


def verified_source_subset(question: str, chunks: list[SourceChunk]) -> list[SourceChunk]:
    """Return the most useful cited pages for deterministic answers."""
    preferred_pages = {
        "salary": {"125", "126"},
        "overtime": {"79", "80"},
        "work_certificate": {"38"},
        "sick_leave": {"98"},
        "termination": {"34", "35"},
        "preavis": {"31"},
        "paid_leave": {"88"},
        "contract": {"18"},
        "maternity_leave": {"64", "65", "66"},
        "notice_job_search": {"30", "31"},
    }

    keep_pages = set()
    for topic in matched_topics(question):
        keep_pages.update(preferred_pages.get(topic, set()))

    selected = [chunk for chunk in chunks if chunk.page in keep_pages]
    return selected or chunks


def answer_from_verified_rules(question: str, chunks: list[SourceChunk]) -> str | None:
    """Return source-backed answers for high-risk recurring legal questions."""
    if not chunks:
        return None

    context = "\n".join(chunk.text for chunk in chunks).lower()
    first_source = first_citation(chunks)

    if question_matches_topic(question, "paid_leave") and "article 231" in context:
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

    if question_matches_topic(question, "salary") and contains_all(
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

    if question_matches_topic(question, "overtime") and contains_all(
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

    if (
        question_matches_topic(question, "work_certificate")
        and "certificat de travail" in context
        and "38" in source_pages(chunks)
    ):
        first_source = next(
            chunk.citation for chunk in chunks if chunk.page == "38"
        )
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

    if question_matches_topic(question, "sick_leave") and contains_all(
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

    if (
        question_matches_topic(question, "termination")
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

    if question_matches_topic(question, "preavis") and contains_all(
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

    if question_matches_topic(question, "contract") and contains_all(
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

    if question_matches_topic(question, "maternity_leave") and (
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

    if question_matches_topic(question, "notice_job_search") and contains_all(
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

    return None


def format_context(chunks: list[SourceChunk]) -> str:
    return "\n\n---\n\n".join(
        f"المصدر {chunk.number} - الصفحة {chunk.page}:\n{chunk.text}"
        for chunk in chunks
    )


def search_law(question: str, n_results: int = N_RESULTS):
    return format_context(retrieve_law(question, n_results=n_results))


def build_messages(question: str, context: str):
    full_structure = should_use_full_structure(question)
    answer_shape = (
        """
استعمل هذا الشكل فقط:

الجواب المختصر:
جملة أو جوج جمل واضحة.

الشرح:
- نقطة 1
- نقطة 2
- نقطة 3

الأساس القانوني:
اذكر المصدر والصفحة فقط.

شنو يدير المستخدم:
خطوات عملية مختصرة.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
"""
        if full_structure
        else """
جاوب بشكل طبيعي ومختصر:
- الجواب المباشر أولا.
- من بعد جوج أو ثلاثة نقاط مفيدة فقط إذا احتاج السؤال.
- من بعد سطر واحد للمصدر بصيغة: المصدر: [المصدر 1، الصفحة 34]
- وختم بتنبيه قصير: هاد الجواب للتوجيه فقط وماشي استشارة قانونية رسمية.

ما تستعملش العناوين الطويلة إلا إذا كان السؤال معقد فعلا.
"""
    )
    system_prompt = f"""
أنت مساعد قانوني مهني مختص فقط فمدونة الشغل المغربية، وماشي محامي وما كتقدمش ضمانات نهائية.

القواعد:
- جاوب غير بالدارجة المغربية وبأسلوب بسيط، مهني، وطبيعي.
- خليك واضح ومفيد، بلا عبارات روبوتية وبلا خلط لغات.
- ما تقولش أنك محامي، وما تعطي حتى ضمانة نهائية أو نتيجة مؤكدة.
- جاوب غير انطلاقا من السياق القانوني اللي عطيتك، وما تستعملش المعرفة العامة.
- أي حكم قانوني خاصو يكون مربوط بالمصدر اللي بان فالسياق.
- ما تخترعش مواد، آجال، إجراءات، مؤسسات، ولا خلاصات ما كايناش فالسياق.
- إلا كان السياق ضعيف، ناقص، أو ما كيجاوبش مباشرة على السؤال، قل بالضبط:
  "{INSUFFICIENT_CONTEXT_MESSAGE}"
- كل جواب قانوني خاصو يذكر مصدر واحد على الأقل بصيغة: [المصدر 1، الصفحة 34]
- ما تستعملش الإنجليزية ولا الصينية ولا الفرنسية فالشرح، إلا فاسم قانوني موجود فالمصدر بحالو.
{answer_shape}
"""

    user_prompt = f"""
السؤال ديال المستخدم:
{question}

السياق القانوني المستخرج من مدونة الشغل:
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

    return any(
        keyword_score(chunk.text, question) >= MIN_RELEVANCE_SCORE
        or anchor_score(chunk.text, question) > 0
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


def answer_is_valid(question: str, answer: str, chunks: list[SourceChunk]) -> bool:
    """Validate generated answers before exposing them to the user."""
    if not answer.strip():
        return False
    if len(answer) > MAX_GENERATED_ANSWER_CHARS:
        return False
    if chunks and not CITATION_PATTERN.search(answer):
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
    conversational_answer = conversation_router(question)
    if conversational_answer:
        return (conversational_answer, []) if return_sources else conversational_answer

    if is_obviously_out_of_scope(question):
        answer = refusal_answer()
        return (answer, []) if return_sources else answer

    chunks = retrieve_law(question, n_results=n_results)

    article_number = asks_for_specific_article(question)
    if article_number and not context_has_article(article_number, chunks):
        answer = refusal_answer()
        return (answer, []) if return_sources else answer

    if not context_is_sufficient(question, chunks):
        answer = refusal_answer()
        return (answer, []) if return_sources else answer

    verified_answer = answer_from_verified_rules(question, chunks)
    if verified_answer:
        chunks = verified_source_subset(question, chunks)
        return (verified_answer, chunks) if return_sources else verified_answer

    context = format_context(chunks)
    messages = build_messages(question, context)

    response = requests.post(
        OLLAMA_CHAT_URL,
        json={
            "model": CHAT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.7,
                "num_ctx": 4096,
                "num_predict": 650,
                "repeat_penalty": 1.15,
                "num_thread": 8,
            },
        },
        timeout=300,
    )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        error_text = response.text.strip()
        raise RuntimeError(f"Ollama chat failed for model '{CHAT_MODEL}': {error_text}") from exc

    answer = response.json()["message"]["content"].strip()

    if chunks and not CITATION_PATTERN.search(answer):
        citations = " ".join(chunk.citation for chunk in chunks[: min(2, len(chunks))])
        answer = f"{answer.rstrip()}\n\nالمصادر: {citations}"

    if not answer_is_valid(question, answer, chunks):
        answer = refusal_answer()
        chunks = []

    return (answer, chunks) if return_sources else answer


def print_sources(chunks: list[SourceChunk]):
    print("\nSources retrieved:")
    for chunk in chunks:
        distance = "" if chunk.distance is None else f", distance={chunk.distance:.4f}"
        print(f"- source {chunk.number}: page {chunk.page}{distance}")


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
