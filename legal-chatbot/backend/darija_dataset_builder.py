# -*- coding: utf-8 -*-
"""Generate and validate the Moroccan Darija intent-normalization dataset.

This dataset is for intent detection and query expansion only. It is not an
SFT/fine-tuning dataset.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data" / "darija_dataset"
INTENTS_PATH = DATA_DIR / "intents.json"
EXAMPLES_PATH = DATA_DIR / "darija_examples.jsonl"
EVAL_PATH = DATA_DIR / "darija_eval.jsonl"
WEAK_CASES_PATH = DATA_DIR / "weak_cases.jsonl"
README_PATH = DATA_DIR / "README.md"

DOMAIN = "moroccan_labor_law"
TARGET_PER_INTENT = 40
EVAL_PER_INTENT = 4

CONVERSATIONAL_INTENTS = {"greeting", "thanks", "goodbye", "unclear", "out_of_scope"}
DIRECT_ONLY_INTENTS = {"greeting", "thanks", "goodbye", "unclear"}

INTENT_DEFINITIONS: dict[str, dict[str, object]] = {
    "greeting": {
        "normalized_query": "",
        "keywords": ["سلام", "salam", "bonjour", "hello", "hi", "labas", "لاباس"],
        "seeds": ["سلام", "salam", "bonjour", "hello", "hi", "سلام عليكم", "labas", "لاباس", "صباح الخير", "مساء الخير"],
    },
    "thanks": {
        "normalized_query": "",
        "keywords": ["شكرا", "merci", "thanks", "baraka", "يعطيك الصحة"],
        "seeds": ["شكرا", "merci", "thanks", "يعطيك الصحة", "بارك الله فيك", "thx", "شكرا بزاف", "مزيان شكرا"],
    },
    "goodbye": {
        "normalized_query": "",
        "keywords": ["باي", "bye", "بسلامة", "مع السلامة", "ila li9a2"],
        "seeds": ["باي", "bye", "بسلامة", "مع السلامة", "الى اللقاء", "سلام دابا", "تشاو", "merci bye"],
    },
    "unclear": {
        "normalized_query": "",
        "keywords": ["شنو", "واش", "ممم", "؟؟", "ما فهمتش"],
        "seeds": ["شنو", "واش", "ما فهمتش", "زيد وضح", "؟؟", "ممم", "كيفاش يعني", "ما عرفتش", "اشنو هادشي"],
    },
    "out_of_scope": {
        "normalized_query": "خارج نطاق مدونة الشغل المغربية",
        "keywords": ["طلاق", "كراء", "حادثة سير", "جنائي", "ارث", "شركة", "تجارة", "دعوى تجارية", "فيزا", "فرنسا", "مخالفة", "code route", "impots"],
        "seeds": ["بغيت نسول على الطلاق", "عندي مشكل فالكراء", "وقعت ليا حادثة سير", "بغيت نقسم الورث", "شيك بلا رصيد شنو ندير", "مشكل مع مول الدار", "ضريبة الشركة", "قانون السير", "قضية جنائية", "كيفاش نرفع دعوى تجارية", "شنو ندير فالإرث", "كيفاش ندير فيزا لفرنسا", "عندي مخالفة فالطريق"],
    },
    "dismissal": {
        "normalized_query": "licenciement فصل طرد تعويض مسطرة الفصل محضر الاستماع سبب مقبول",
        "keywords": ["طرد", "خرج", "وقف", "حبس", "licenciement", "فصل", "الباطرون", "خدمة"],
        "seeds": ["طردوني", "خرجوني من الخدمة", "قالو ليا ما تبقاش تجي للخدمة", "حبسوني من الخدمة", "وقفوني", "سالاو معايا", "الباطرون خرجني", "ما بقاوش عيطو ليا"],
    },
    "disciplinary_dismissal": {
        "normalized_query": "faute grave خطأ جسيم مسطرة تأديبية محضر الاستماع الفصل التأديبي",
        "keywords": ["خطأ جسيم", "faute grave", "مجلس تأديبي", "استماع", "محضر", "تأديبي"],
        "seeds": ["قالو ليا درت خطأ جسيم", "بغاو يطردوني faute grave", "عيطو ليا للاستماع قبل الطرد", "دارو ليا محضر الاستماع", "فصل تأديبي شنو حقي", "طردوني بسبب الغياب", "قالو سبّيت المدير", "بغاو يديرو ليا مسطرة تأديبية"],
    },
    "resignation": {
        "normalized_query": "démission استقالة مغادرة العمل إرادة الأجير إشعار",
        "keywords": ["استقالة", "démission", "demission", "نستاقل", "نحبس الخدمة", "نمشي"],
        "seeds": ["بغيت نستاقل", "كتبت الاستقالة وندمت", "واش نقدر نحبس الخدمة", "demission شنو فيها", "بغيت نمشي من الشركة", "دفعت الاستقالة", "جبروني نكتب استقالة", "هددوني باش نستاقل"],
    },
    "salary_unpaid": {
        "normalized_query": "salaire الأجر عدم أداء الأجر paiement du salaire تأخر الأجرة",
        "keywords": ["خلص", "صالير", "salaire", "الأجر", "ما عطانيش", "تخلصتش"],
        "seeds": ["ما خلصنيش", "ما عطانيش الصالير", "الباطرون باقي ما خلصنيش", "خدمت وما تخلصتش", "ما عطاونيش الأجر ديالي", "salaire باقي", "الشهر داز بلا خلاص", "فين هو الصالير ديالي"],
    },
    "salary_deduction": {
        "normalized_query": "retenue sur salaire اقتطاع من الأجر خصم الأجرة عقوبة مالية",
        "keywords": ["نقص", "قطع", "اقتطاع", "خصم", "retenue", "deduction", "صالير"],
        "seeds": ["نقصو ليا من الصالير", "قطعو ليا من الأجر", "دارو ليا اقتطاع", "خصمو ليا فلوس", "retenue sur salaire واش قانونية", "نقص ليا نهار كامل", "خداو ليا من الخلاص", "عاقبوني بفلوس"],
    },
    "overtime": {
        "normalized_query": "heures supplémentaires الساعات الإضافية السوايع الزايدة تعويض الزيادة",
        "keywords": ["سوايع", "زايدة", "overtime", "heures sup", "اضافية", "زيادة"],
        "seeds": ["خدمت سوايع زايدة", "ما خلصونيش overtime", "heures sup ما تخلصتش", "كنخدم حتى لليل", "الساعات الإضافية شحال كتخلص", "زادوني فالوقت بلا فلوس", "خدمت نهار الأحد", "خدمت فوق الوقت"],
    },
    "annual_leave": {
        "normalized_query": "congé annuel العطلة السنوية الكونجي الإجازة السنوية مؤدى عنها",
        "keywords": ["كونجي", "congé", "conge", "عطلة", "اجازة", "سنوية"],
        "seeds": ["بغيت الكونجي ديالي", "رفضو يعطيو ليا congé", "العطلة السنوية شحال", "ما عطاونيش الكونجي", "واش الكونجي خالص", "بغيت ناخد الاجازة", "حرمني من العطلة", "conge annuel"],
    },
    "sick_leave": {
        "normalized_query": "maladie congé maladie شهادة طبية رخصة مرضية غياب بسبب المرض",
        "keywords": ["مرض", "طبيب", "شهادة طبية", "sick", "maladie", "رخصة"],
        "seeds": ["مرضت وما مشيتش للخدمة", "عندي شهادة طبية", "كونجي مرضي", "طردوني حيث مرضت", "sick leave واش خالص", "عطيتهم certificat medical", "غبت بسبب المرض", "بغيت رخصة مرضية"],
    },
    "maternity": {
        "normalized_query": "maternité grossesse congé maternité حماية المرأة الحامل الولادة",
        "keywords": ["حامل", "حمل", "ولادة", "maternité", "maternite", "grossesse"],
        "seeds": ["أنا حاملة وكنخدم", "بغيت كونجي الولادة", "طردوني حيث حاملة", "congé maternité شحال", "grossesse فالخدمة", "حقوق المرأة الحامل", "قربت نولد", "المشغل ما باغيش الحمل"],
    },
    "work_accident": {
        "normalized_query": "accident du travail حادثة شغل إصابة مهنية تصريح حادث الشغل تعويض",
        "keywords": ["حادث", "تجرح", "تكسرت", "طاحت", "ماكينة", "accident", "فالخدمة"],
        "seeds": ["وقع ليا حادث فالخدمة", "تجرحت وأنا خدام", "طاحت عليا حاجة فالخدمة", "تكسرت فالخدمة", "دزتني ماكينة فالخدمة", "وقع ليا accident فالشغل", "تحرقت فالمعمل", "تزحلقت فالشركة"],
    },
    "cnss": {
        "normalized_query": "CNSS الضمان الاجتماعي التصريح بالأجير الاشتراكات الصندوق الوطني للضمان الاجتماعي",
        "keywords": ["cnss", "ضمان", "تصريح", "مصرحش", "سجلني", "cotisation"],
        "seeds": ["ما مصرحش بيا ف cnss", "واش خاصو يسجلني فالضمان", "ما كايناش CNSS", "بغيت نعرف التصريح ديالي", "المشغل ما كيخلصش cotisation", "مصرح بيا ناقص", "فين نمشي للضمان", "ما مسجلنيش"],
    },
    "work_certificate": {
        "normalized_query": "certificat de travail شهادة العمل شهادة الشغل عند انتهاء العقد",
        "keywords": ["شهادة العمل", "شهادة الشغل", "certificat", "attestation", "خروج"],
        "seeds": ["بغيت شهادة العمل", "رفض يعطيني certificat de travail", "شهادة الشغل من حقي", "خرجت وما عطاونيش attestation", "شنو ندير باش ناخد شهادة العمل", "ما عطانيش شهادة الخدمة", "certificat بعد الطرد", "بغيت ورقة الخدمة"],
    },
    "contract_cdd_cdi": {
        "normalized_query": "contrat de travail CDD CDI عقد شغل مدة محددة غير محددة",
        "keywords": ["cdd", "cdi", "كونطرا", "عقد", "contrat", "مدة محددة"],
        "seeds": ["شنو الفرق بين CDD و CDI", "عندي كونطرا CDD", "بغاو يبدلو ليا العقد", "contrat ديالي سالا", "CDI شنو كيعني", "عقد محدد المدة", "جددو ليا CDD بزاف", "بغيت نفهم الكونطرا"],
    },
    "no_written_contract": {
        "normalized_query": "contrat non écrit preuve relation de travail عقد شفوي إثبات علاقة الشغل",
        "keywords": ["بلا عقد", "بلا كونطرا", "عقد مكتوب", "شفوي", "preuve", "contrat"],
        "seeds": ["خدام بلا عقد", "ما عنديش كونطرا", "خدمت بلا ورقة", "العقد غير بالشفوي", "بغيت نثبت الخدمة", "ما عطاونيش عقد مكتوب", "واش بلا contrat عندي حق", "عندي غير رسائل واتساب"],
    },
    "preavis": {
        "normalized_query": "préavis délai de préavis الإشعار الإخطار تعويض الإخطار مدة الإنذار",
        "keywords": ["preavis", "préavis", "اشعار", "إشعار", "انذار", "اخطار", "مدة"],
        "seeds": ["شنو هو preavis", "خاصني نخدم مدة الإنذار", "خرجوني بلا préavis", "تعويض الإشعار شحال", "ما عطاونيش اخطار", "بغيت نعرف مدة preavis", "واش خاصهم يعلموني قبل الطرد", "الانذار قبل الخروج"],
    },
    "working_time": {
        "normalized_query": "durée du travail ساعات العمل 44 ساعة مدة الشغل الراحة الأسبوعية",
        "keywords": ["ساعات العمل", "44", "وقت", "دوام", "horaire", "durée", "راحة"],
        "seeds": ["شحال ساعات العمل فالقانون", "كنخدم 12 ساعة فالنهار", "44 ساعة واش قانونية", "وقت الخدمة طويل", "horaire ديال الخدمة", "ما كايناش الراحة", "دوام كامل شحال", "مدة الشغل فالأسبوع"],
    },
    "internal_rules": {
        "normalized_query": "règlement intérieur النظام الداخلي للمقاولة العقوبات التأديبية قواعد العمل",
        "keywords": ["نظام داخلي", "règlement", "reglement", "قانون داخلي", "عقوبة", "قاعدة"],
        "seeds": ["شنو هو النظام الداخلي", "الشركة عندها قانون داخلي", "عاقبوني حسب règlement intérieur", "ما عرفتوش القواعد", "النظام الداخلي ما عطاوهش لينا", "علقو قانون داخلي", "واش العقوبة فالنظام الداخلي", "reglement ديال الشركة"],
    },
    "labor_inspection": {
        "normalized_query": "inspection du travail مفتش الشغل نزاع الشغل محاولة الصلح شكاية",
        "keywords": ["مفتش", "تفتيش", "inspection", "inspecteur", "شكاية", "نزاع"],
        "seeds": ["بغيت نمشي لمفتش الشغل", "فين ندير شكاية على الباطرون", "inspection du travail", "مفتش الشغل يقدر يعاونني", "عندي نزاع فالشغل", "بغيت صلح مع الشركة", "واش نمشي للتفتيش", "inspecteur du travail"],
    },
    "union": {
        "normalized_query": "syndicat نقابة الحرية النقابية الانتماء النقابي حماية النقابيين",
        "keywords": ["نقابة", "syndicat", "syndical", "مندوب نقابي", "انخراط"],
        "seeds": ["بغيت ندخل للنقابة", "طردوني حيث نقابي", "syndicat فالخدمة", "واش عندي حق ننخرط", "المدير ما باغيش النقابة", "ضغطو عليا نخرج من النقابة", "مندوب نقابي", "الحرية النقابية"],
    },
    "employee_representative": {
        "normalized_query": "délégué des salariés ممثل الأجراء مندوب الأجراء انتخابات تمثيلية العمال",
        "keywords": ["ممثل الأجراء", "مندوب الأجراء", "délégué", "delegue", "انتخابات", "ممثلي"],
        "seeds": ["شنو دور ممثل الأجراء", "بغيت نترشح مندوب الأجراء", "délégué des salariés", "انتخابات ممثلي العمال", "واش المندوب محمي", "الشركة ما بغاتش ممثلين", "مندوب الأجراء عاونني", "حقوق ممثل الأجراء"],
    },
}

PREFIXES = [
    "",
    "عافاك ",
    "سمح ليا ",
    "بغيت نعرف ",
    "واش قانونيا ",
    "شنو ندير إلا ",
    "صاحبي قال ليا ",
    "أنا مقلق حيت ",
    "ضروري جاوبني ",
    "فالمغرب ",
]

SUFFIXES = [
    "",
    " شنو ندير؟",
    " واش عندي حق؟",
    " شنو القانون؟",
    " واش هادشي عادي؟",
    " فمدونة الشغل؟",
    " وبغيت نفهم حقي",
    " الله يجازيك",
    " وما فهمتش المسطرة",
    " دابا",
]


def required_intents() -> list[str]:
    return list(INTENT_DEFINITIONS)


def make_id(intent: str, index: int) -> str:
    return f"{intent}_{index:03d}"


def row_for(intent: str, question: str, index: int) -> dict[str, object]:
    definition = INTENT_DEFINITIONS[intent]
    should_search = intent not in CONVERSATIONAL_INTENTS
    return {
        "id": make_id(intent, index),
        "intent": intent,
        "darija_question": " ".join(question.split()),
        "normalized_query": definition["normalized_query"],
        "domain": DOMAIN,
        "should_search_rag": should_search,
    }


def generate_questions(intent: str, target: int) -> list[str]:
    seeds = list(INTENT_DEFINITIONS[intent]["seeds"])  # type: ignore[index]
    questions: list[str] = []
    seen: set[str] = set()

    candidates: list[str] = []
    candidates.extend(seeds)
    for seed in seeds:
        for prefix in PREFIXES:
            for suffix in SUFFIXES:
                candidates.append(f"{prefix}{seed}{suffix}")
    for seed in seeds:
        candidates.extend(
            [
                seed.replace("الخدمة", "الخدمه"),
                seed.replace("الشغل", "الشغل ديالي"),
                seed.replace("واش", "wach"),
                seed.replace("شنو", "chno"),
            ]
        )

    for candidate in candidates:
        normalized = " ".join(candidate.split()).strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        questions.append(normalized)
        seen.add(key)
        if len(questions) >= target:
            break

    if len(questions) < target:
        raise ValueError(f"Intent {intent} only generated {len(questions)} examples")
    return questions


def build_examples() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_questions: set[str] = set()

    for intent in required_intents():
        index = 1
        for question in generate_questions(intent, TARGET_PER_INTENT * 2):
            key = question.casefold()
            if key in seen_questions:
                continue
            rows.append(row_for(intent, question, index))
            seen_questions.add(key)
            index += 1
            if index > TARGET_PER_INTENT:
                break

        if index <= TARGET_PER_INTENT:
            raise ValueError(f"Intent {intent} has fewer than {TARGET_PER_INTENT} unique rows")

    return rows


def build_eval(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_intent: dict[str, list[dict[str, object]]] = {intent: [] for intent in required_intents()}
    for row in rows:
        by_intent[str(row["intent"])].append(row)

    eval_rows: list[dict[str, object]] = []
    for intent in required_intents():
        # Use examples from later in the generated block so the eval set is
        # stable and still covers short, mixed, vague, and prefixed wording.
        for source in by_intent[intent][-EVAL_PER_INTENT:]:
            eval_rows.append(
                {
                    "id": f"eval_{source['id']}",
                    "question": source["darija_question"],
                    "expected_intent": intent,
                    "expected_normalized_query": source["normalized_query"],
                    "should_search_rag": source["should_search_rag"],
                }
            )
    return eval_rows


def validate_rows(rows: list[dict[str, object]]) -> None:
    required_fields = {
        "id",
        "intent",
        "darija_question",
        "normalized_query",
        "domain",
        "should_search_rag",
    }
    ids = Counter(str(row.get("id", "")) for row in rows)
    questions = Counter(str(row.get("darija_question", "")).casefold() for row in rows)
    errors: list[str] = []

    for line_number, row in enumerate(rows, start=1):
        missing = [field for field in required_fields if field not in row]
        if missing:
            errors.append(f"line {line_number}: missing fields {missing}")
        if row.get("intent") not in INTENT_DEFINITIONS:
            errors.append(f"line {line_number}: unknown intent {row.get('intent')}")
        if row.get("domain") != DOMAIN:
            errors.append(f"line {line_number}: invalid domain")
        if not isinstance(row.get("should_search_rag"), bool):
            errors.append(f"line {line_number}: should_search_rag must be boolean")
        if row.get("intent") in DIRECT_ONLY_INTENTS and row.get("should_search_rag") is not False:
            errors.append(f"line {line_number}: direct intent should not search RAG")
        if row.get("intent") == "out_of_scope" and row.get("should_search_rag") is not False:
            errors.append(f"line {line_number}: out_of_scope should not search RAG")

    duplicate_ids = [value for value, count in ids.items() if count > 1]
    duplicate_questions = [value for value, count in questions.items() if value and count > 1]
    if duplicate_ids:
        errors.append(f"duplicate ids: {duplicate_ids[:5]}")
    if duplicate_questions:
        errors.append(f"duplicate questions: {duplicate_questions[:5]}")

    counts = Counter(str(row["intent"]) for row in rows)
    for intent in required_intents():
        if counts[intent] < TARGET_PER_INTENT:
            errors.append(f"weak intent {intent}: {counts[intent]} rows")

    if errors:
        raise ValueError("\n".join(errors))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_readme() -> None:
    README_PATH.write_text(
        """# Moroccan Darija Legal Understanding Dataset

This folder contains the first-stage understanding layer for Lmo7ami AI. It is
used to detect informal Moroccan Darija labor-law intent, normalize the query
with Arabic/French legal keywords, and decide whether the RAG pipeline should be
called.

Files:

- `intents.json`: intent metadata, keywords, and normalized legal queries.
- `darija_examples.jsonl`: generated Darija examples for intent detection.
- `darija_eval.jsonl`: held-out evaluation questions with expected intents.
- `weak_cases.jsonl`: manually collected failures to review and fold into the generator.

This is not a fine-tuning dataset yet. Keep it source-controlled, review weak
cases, then regenerate with `python darija_dataset_builder.py`.
""",
        encoding="utf-8",
    )


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    examples = build_examples()
    validate_rows(examples)
    eval_rows = build_eval(examples)

    intents_payload = {
        "domain": DOMAIN,
        "minimum_examples": len(examples),
        "required_intents": required_intents(),
        "conversational_intents": sorted(CONVERSATIONAL_INTENTS),
        "legal_intents": [intent for intent in required_intents() if intent not in CONVERSATIONAL_INTENTS],
        "intents": INTENT_DEFINITIONS,
    }

    write_json(INTENTS_PATH, intents_payload)
    write_jsonl(EXAMPLES_PATH, examples)
    write_jsonl(EVAL_PATH, eval_rows)
    if not WEAK_CASES_PATH.exists():
        write_jsonl(WEAK_CASES_PATH, [])
    write_readme()

    counts = Counter(str(row["intent"]) for row in examples)
    print(f"Generated {len(examples)} examples")
    print(f"Generated {len(eval_rows)} eval cases")
    print("Intent distribution:")
    for intent in required_intents():
        print(f"- {intent}: {counts[intent]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
