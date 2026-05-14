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
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
N_RESULTS = int(os.getenv("RAG_N_RESULTS", "2"))

INSUFFICIENT_CONTEXT_MESSAGE = (
    "ما لقيتش جواب قانوني كافي فالمصدر المتوفر."
)
LEGAL_TOPIC_TERMS = {
    "sick_leave": [
      "مرض",
    "المرض",
    "مريض",
    "طبيب",
    "شهادة طبية",
    "غياب بسبب المرض",
    "maladie",
    "absence pour maladie",
    "certificat médical",
    "certificat medical",
    ],
    "termination": [
        "طرد",
        "فصل",
        "خروج",
        "إنذار",
        "انذار",
        "licenciement",
        "préavis",
        "preavis",
        "indemnité de licenciement",
        "dommages-intérêts",
    ],
    "paid_leave": [
        "كونجي",
        "عطلة",
        "اجازة",
        "إجازة",
        "سنوي",
        "congé annuel payé",
        "conge annuel paye",
        "jour et demi",
        "Article 231",
    ],
}
OUT_OF_SCOPE_TERMS = [
    "حادثة سير",
    "حادتة سير",
    "الطريق العام",
    "code de la route",
    "طلاق",
    "كراء",
    "كريت",
    "مول الدار",
    "تجارية",
    "تجاري",
    "دعوى تجارية",
]
WORK_RELATED_TERMS = [
    "خدمة",
    "الشغل",
    "العمل",
    "عامل",
    "أجير",
    "اجير",
    "employeur",
    "salarié",
    "travail",
]
CITATION_PATTERN = re.compile(r"\[المصدر\s+\d+،\s+الصفحة\s+[^\]]+\]")

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
    """Shape RTL Arabic for terminals that do not render Arabic correctly."""
    if not arabic_reshaper or not get_display:
        return text

    return "\n".join(
        get_display(arabic_reshaper.reshape(line))
        for line in text.splitlines()
    )


def terminal_print(text: str = ""):
    print(terminal_text(text))


def get_embedding(text: str):
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={
            "model": EMBED_MODEL,
            "prompt": text,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def is_obviously_out_of_scope(question: str) -> bool:
    normalized = question.lower()
    has_out_of_scope_term = any(term in normalized for term in OUT_OF_SCOPE_TERMS)
    has_work_term = any(term in normalized for term in WORK_RELATED_TERMS)
    return has_out_of_scope_term and not has_work_term


def question_matches_topic(question: str, topic: str) -> bool:
    normalized = question.lower()
    return any(term.lower() in normalized for term in LEGAL_TOPIC_TERMS[topic])


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
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = get_embedding(expand_legal_query(question))
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results.get("distances", [[]])[0]

    chunks = []
    for index, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
        page = meta.get("page", "unknown")
        clean_doc = doc.strip().replace("\n\n", "\n")
        distance = distances[index - 1] if index - 1 < len(distances) else None
        chunks.append(
            SourceChunk(
                number=index,
                page=str(page),
                text=clean_doc,
                distance=distance,
            )
        )

    chunks = add_keyword_results(collection, question, chunks)
    chunks.sort(
        key=lambda chunk: (
            keyword_score(chunk.text, question),
            0 if chunk.distance is None else -chunk.distance,
        ),
        reverse=True,
    )

    for index, chunk in enumerate(chunks[:n_results], start=1):
        chunks[index - 1] = SourceChunk(
            number=index,
            page=chunk.page,
            text=chunk.text,
            distance=chunk.distance,
        )

    return chunks[:n_results]


def answer_from_verified_rules(question: str, chunks: list[SourceChunk]) -> str | None:
    context = "\n".join(chunk.text for chunk in chunks).lower()
    first_source = chunks[0].citation if chunks else "[المصدر 1، الصفحة unknown]"

    if question_matches_topic(question, "paid_leave") and "article 231" in context:
        return f"""
الجواب المختصر:
إلا كان عندك 6 شهور ديال الخدمة المتواصلة عند نفس المشغل، عندك الحق فالعطلة السنوية المؤدى عنها: نهار ونص ديال العمل الفعلي على كل شهر خدمة. إلا كان الأجير أقل من 18 عام، الحق هو جوج أيام ديال العمل الفعلي على كل شهر خدمة. {first_source}

الشرح:
مدونة الشغل كتربط الحق فالعطلة السنوية المؤدى عنها بمرور 6 أشهر ديال الخدمة المتواصلة، وكتحسب المدة حسب عدد شهور الخدمة. {first_source}

الأساس القانوني:
المصدر كيهضر على Article 231: congé annuel payé، وكيحدد 1.5 يوم عمل فعلي لكل شهر خدمة، و2 أيام لكل شهر بالنسبة للأجراء أقل من 18 سنة. {first_source}

شنو يدير المستخدم:
حسب شحال خدمتي من شهر بعد أول 6 شهور، ضرب عدد الشهور فـ 1.5 يوم. وراجع العقد أو الاتفاقية الجماعية إلا كانت كتعطي شروط أحسن.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
""".strip()

    return None


def format_context(chunks: list[SourceChunk]) -> str:
    context_parts = []
    for chunk in chunks:
        context_parts.append(
            f"المصدر {chunk.number} - الصفحة {chunk.page}:\n{chunk.text}"
        )

    return "\n\n---\n\n".join(context_parts)


def search_law(question: str, n_results: int = N_RESULTS):
    return format_context(retrieve_law(question, n_results=n_results))


def build_messages(question: str, context: str):
    system_prompt = f"""
أنت مساعد قانوني مغربي متخصص في مدونة الشغل المغربية.

أجب بالدارجة المغربية فقط، وبجمل قصيرة ومفهومة.
لا تخلط اللغات.
لا تكتب جملة ناقصة.
لا تعطِ جواباً طويلاً.
اعتمد فقط على السياق القانوني المقدم.
إذا لم يكن السياق كافياً، قل: "{INSUFFICIENT_CONTEXT_MESSAGE}"

استعمل هذا الشكل فقط:

الجواب المختصر:
جملة أو جوج جمل واضحة.

الشرح:
شرح بسيط في 3 نقاط كحد أقصى.

الأساس القانوني:
اذكر المصدر والصفحة فقط.

شنو يدير المستخدم:
خطوات عملية مختصرة.

تنبيه:
هاد الجواب للمعلومة فقط وماشي استشارة قانونية رسمية.
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


def ask_chatbot(question: str, n_results: int = N_RESULTS, return_sources: bool = False):
    if is_obviously_out_of_scope(question):
        answer = (
            f"{INSUFFICIENT_CONTEXT_MESSAGE}\n\n"
            "تنبيه: هاد المساعد محدود فمدونة الشغل المغربية، والسؤال باين خارج هاد النطاق."
        )
        if return_sources:
            return answer, []
        return answer

    chunks = retrieve_law(question, n_results=n_results)
    verified_answer = answer_from_verified_rules(question, chunks)
    if verified_answer:
        if return_sources:
            return verified_answer, chunks
        return verified_answer

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
                 "num_predict": 700,
                 "repeat_penalty": 1.15
                }
        },
        timeout=300,
    )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        error_text = response.text.strip()
        raise RuntimeError(
            f"Ollama chat failed for model '{CHAT_MODEL}': {error_text}"
        ) from exc

    answer = response.json()["message"]["content"]
    if chunks and not CITATION_PATTERN.search(answer):
        citations = " ".join(chunk.citation for chunk in chunks[: min(2, len(chunks))])
        answer = f"{answer.rstrip()}\n\nالمصادر: {citations}"

    if return_sources:
        return answer, chunks

    return answer


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
            terminal_print("\nجاري البحث والجواب...\n")
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

