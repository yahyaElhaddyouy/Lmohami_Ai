# -*- coding: utf-8 -*-
"""Evaluate Moroccan Darija comprehension and pre-RAG routing.

The set is intentionally broad: ordinary Darija should get a direct Darija
response without legal citations, while labor-law questions should still enter
the legal RAG path and return cited sources.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests

from conversation_classifier import classify_conversation
from rag import ask_chatbot


BASE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = BASE_DIR / "darija_comprehension_results.jsonl"
FAILURES_PATH = BASE_DIR / "darija_comprehension_failures.jsonl"
REPORT_PATH = BASE_DIR / "darija_comprehension_report.md"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


CASE_GROUPS: list[dict[str, Any]] = [
    {
        "category": "greetings",
        "expected_type": "greeting",
        "questions": [
            "السلام عليكم",
            "سلام",
            "salam",
            "salam alikom",
            "bonjour",
            "hello",
            "hi",
            "صباح الخير",
            "مسا الخير",
            "ahlan",
            "labas",
            "سلام عليكم خويا",
            "salam khoya",
            "السلام",
            "salam alaikom",
        ],
    },
    {
        "category": "thanks",
        "expected_type": "thanks",
        "questions": [
            "شكرا",
            "شكرا بزاف",
            "بارك الله فيك",
            "يعطيك الصحة",
            "merci",
            "thanks",
            "thank you",
            "lah yhafdek",
            "chokran",
            "chokran bzaf",
            "الله يجازيك بخير",
            "مزيان شكرا",
            "merci khoya",
            "thx",
            "شكرا خويا",
        ],
    },
    {
        "category": "daily_darija",
        "expected_type": "general_conversation",
        "questions": [
            "الجو سخون بزاف",
            "الجو بارد اليوم",
            "واش كتعرف كازا",
            "كازا عامرة بزاف",
            "شنو واقع اليوم",
            "نهاري داز عادي",
            "بغيت غير نهضر شوية",
            "واش كتفهم الدارجة",
            "شنو كتدير دابا",
            "كيف داير مع العطلة",
            "واش كاين شي جديد",
            "بغيت نسولك سؤال عام",
            "هاد النهار طويل بزاف",
            "هادشي عجيب شوية",
            "واش نقدر نهضر معاك بالدارجة",
            "بغيت نحكي ليك واحد الحاجة",
            "شنو رأيك فالدارجة المغربية",
            "كتعرف مراكش",
            "بغيت نضحك شوية",
            "راه الجو مزيان",
            "شحال خاصني من دقيق باش ندير مسمن",
            "بغيت وصفة ديال الحريرة",
            "فين نمشي نتقضى فالقرب",
            "شنو ندير للعشا",
            "بغيت نمشي لكازا غدا",
            "الطوبيس تأخر عليا",
            "التلفون ديالي طفا",
            "واش نشري قهوة ولا أتاي",
            "بغيت نسافر لمراكش فالويكاند",
            "شنو أحسن وقت نمشي للبحر",
            "الدار خاصها تنقية",
            "خاصني نشري خبز",
            "شنو ندير اليوم فالدار",
            "الطاكسي غالي بزاف",
            "بغيت نشري حوايج جداد",
            "فين كاين السوق",
            "شنو ندير إلا ضاع ليا الشارجور",
            "واش الماكلة واجدة",
            "بغيت نوجد القهوة",
            "الحي فيه الضجيج بزاف",
            "شنو نوجد للفطور",
            "واش كتعرف طنجة",
            "القهوة بردات",
            "خاصني نرتب الدار",
            "فين كاين أقرب مول",
            "بغيت نمشي نتمشى",
            "الطريق عامرة",
            "واش كاينة شي فكرة للويكاند",
            "عطيني شي جملة بالدارجة",
            "بغيت نتعلم كلمات مغربية",
        ],
    },
    {
        "category": "emotions",
        "expected_type": "general_conversation",
        "questions": [
            "ana m9ele9 bzaf",
            "ana lyouma far7an",
            "مقلق بزاف اليوم",
            "حاس براسي تعبان",
            "ما فاهم والو",
            "قلبي عامر شوية",
            "فرحان حيت نجحت",
            "حشمت بزاف",
            "تقلقت من هادشي",
            "بغيت غير نرتاح شوية",
            "حاس براسي مضغوط",
            "mab9itch 9ader",
            "ana z3fan chwiya",
            "ma fhemt walo",
            "kan7ess b stress",
            "khayef chwiya",
            "فرحت بزاف",
            "محبط شوية",
            "قلقان وما عرفت علاش",
            "t3yit بزاف",
            "راسي عامر بالهضرة",
            "ما عنديش نفس نهضر",
            "بغيت غير شي كلمة زوينة",
            "اليوم طاقتي ناقصة",
            "حاس براسي وحداني",
            "فرحان بزاف بهاد الخبر",
            "مخلوع شوية",
            "مضايق وما عرفت السبب",
            "bghit nrtah chwya",
            "ana 3yan lyoum",
            "kan7ess brassi mchaوش",
            "hadchi daz 3lia tqil",
            "ma b9itch fahm rassi",
            "bghit chi kalma t-hdeni",
            "مقلق من الغد",
            "قلبي مخنوق شوية",
            "حسيت براسي مرتاح دابا",
            "كانحس براسي عيان",
            "lyoum makaynach énergie",
            "je suis stressé chwiya",
        ],
    },
    {
        "category": "meaning_questions",
        "expected_type": "general_conversation",
        "questions": [
            "شنو كتعني: الجو سخون بزاف وماقديتش نخرج",
            "شنو كتعني دابا نجي عندك",
            "شنو كتعني هاد الجملة",
            "فهمني شنو معنى بزاف",
            "واش كتفهم إلا قلت ليك بغيت نرتاح",
            "شنو معنى نوض دابا",
            "شنو كتعني ماعنديش نفس",
            "فهمني هاد الدارجة عفاك",
            "شنو كتعني لاباس عليك",
            "شنو معنى تهلا فراسك",
            "واش تفهمني إلا قلت ليك ماقديتش",
            "شنو كتعني راه الحالة صعيبة",
            "شنو معنى عندي الزهر",
            "فهمني كلمة تبرزيط",
            "شنو كتعني مخنوق",
            "واش كتفهم هاد العبارة",
            "شنو معنى نجي من بعد",
            "فهمني دابا شنو ندير فهاد الكلام",
            "شنو كتعني ماشي مشكل",
            "شنو معنى واخا",
            "فهمني كلمة صافي",
            "شنو معنى غير بشوية",
            "شنو كتعني راه دازت",
            "واش فهمتي إلا قلت لك ماكاين باس",
            "شنو معنى دير راسك مافاهمش",
            "فهم ليا كلمة زعما",
            "شنو كتعني بالعربية: هادشي بزاف",
            "شنو معنى نمشي دابا",
            "فهمني جملة ماعندي ما نقول",
            "شنو معنى راه قريب",
            "شنو كتعني كلمة عفاك",
            "واش كتفهم دارجة الشمال",
            "شنو معنى نوض نوض",
            "فهمني كلمة حدايا",
            "شنو كتعني بالدارجة لا باس",
            "شنو معنى شوية بشوية",
            "واش كتعرف معنى عندي الخاطر",
            "فهمني كلمة مخربق",
            "شنو كتعني نجيك من بعد",
            "شنو معنى ماشي دابا",
        ],
    },
    {
        "category": "arabizi",
        "expected_type": "general_conversation",
        "questions": [
            "ana m9ele9 bzaf",
            "wach katfhem darija",
            "chno kat3ni daba nji 3ndek",
            "bghit ghir nhder m3ak",
            "lweather skhoun bzaf",
            "ma fhemt walo",
            "ana fer7an lyoum",
            "fin kayna casa",
            "bghit nrtah chwya",
            "hadchi zwin",
            "lah ykhlik fhemini",
            "wach nji daba",
            "mab9itch 9ader nsber",
            "kan7ess brassi 3yan",
            "bghit chi fikra",
            "ch7al hadi",
            "had lhala m9ewda chwiya",
            "safi fhemt",
            "wach kayn chi haja jdida",
            "ana daba f casa",
            "kifach ndir atay",
            "chno ndir l3cha",
            "fin nmchi lyoum",
            "baghi ntmcha chwiya",
            "daba mazal bekri",
            "bghit ntsenna chwya",
            "kat3ref marrakech",
            "ana bikhir daba",
            "had lmessage mafhemtouch",
            "wach t9der tشرح lia",
            "3afak fhemni had lhedra",
            "mzyan bzaf",
            "hadchi ma3jebnich",
            "baghi nbdl lmawdo3",
            "wach nti m3aya",
            "chno howa lma3na",
            "fin kayn lbus",
            "bghit nkteb message b darija",
            "ana mazal kanfker",
            "safi daba nqder nmchi",
        ],
    },
    {
        "category": "mixed_french_darija",
        "expected_type": "general_conversation",
        "questions": [
            "ana fatigué lyoum",
            "bghit comprendre had lmessage",
            "wach possible nhder b darija et français",
            "had situation bizarre chwiya",
            "ana stressé mais labas",
            "bghit juste discuter chwia",
            "lyoum kayn bouchon بزاف",
            "mon téléphone طاح",
            "service dyal café mzyan",
            "j'ai besoin nرتاح شوية",
            "wach nta comprends darija",
            "ana content بزاف",
            "had plan ماعجبنيش",
            "bghit conseil général",
            "lyoum météo سخونة",
            "je suis perdu chwiya",
            "had l'idée zwina",
            "wach daba nji chez toi",
            "ana occupé daba",
            "merci بزاف على الشرح",
            "je veux comprendre had lkelma",
            "c'est normal ila gelt safi",
            "had message فيه darija بزاف",
            "bghit traduction بسيطة",
            "mon ami قال ليا واخا",
            "planning dyal weekend zwin",
            "restaurant كان عامر",
            "transport اليوم صعيب",
            "j'ai faim شنو ناكل",
            "la ville عامرة",
            "je suis content اليوم",
            "حسيت براسي fatigué",
            "bghit expliquer lma3na",
            "café سخون بزاف",
            "problème dyal téléphone",
        ],
    },
    {
        "category": "general_conversation",
        "expected_type": "general_conversation",
        "questions": [
            "بغيت غير نهضر معاك على الماكلة فالمغرب",
            "شحال خاصني من دقيق باش ندير مسمن؟",
            "بغيت نصائح باش نسافر لمراكش هاد الويكاند",
            "mama mrida bghit n3rf fin nmchi",
            "salam wach katfhem darija?",
            "واش كتفهم إلا قلت ليك بغيت غير نرتاح شوية؟",
            "wach fhemtini ila gelt lik rah lhala m9ewda chwiya?",
            "bghit nfhem wach had lmessage kayban fih mochkil f service",
            "chef dyali kayضغط 3lia بزاف وانا تعييت",
            "شنو ندير باش نتعلم الدارجة",
            "واش تقدر تشرح ليا شي كلمة",
            "بغيت نكتب مساج لصاحبي بالدارجة",
            "شنو الفرق بين بزاف وشوية",
            "واش كتعرف الأمثال المغربية",
            "عطيني مثال ديال هضرة محترمة",
            "كيفاش نقول شكرا بطريقة مغربية",
            "شنو نجاوب إلا قالو ليا لاباس",
            "بغيت نفهم هاد العبارة قبل ما نجاوب",
            "واش ممكن نهضر معاك غير شوية",
            "شنو معنى تهلا فراسك فالهضرة",
        ],
    },
    {
        "category": "non_labor_law_legal",
        "expected_type": "non_labor_law_legal",
        "questions": [
            "كيفاش ندير طلاق اتفاقي",
            "بغيت نسول على النفقة",
            "عندي مشكل فالحضانة",
            "مول الدار بغا يخرجني من الكراء",
            "شنو ندير فالإرث",
            "عندي ملف جنائي",
            "البوليس وقفني شنو ندير",
            "عندي مخالفة فالطريق",
            "حادثة سير فالطريق العام",
            "كيفاش نرفع دعوى تجارية",
            "بغيت نسجل شركة تجارية",
            "عندي مشكل مع الجار",
            "ضريبة الشركة شنو ندير فيها",
            "مشكل مع البنك",
            "كيفاش ندير فيزا لفرنسا",
            "قضية ديال شيك",
            "دعوى على الكراء",
            "مشكل فالعقار",
            "الهجرة لكندا شنو خاصها",
            "code route شنو كيعني",
            "بغيت محامي فالطلاق",
            "الشرطة عيطات ليا",
            "نزاع ديال الورث",
            "كراء محل تجاري",
            "مخالفة السرعة",
        ],
    },
    {
        "category": "labor_law",
        "expected_type": "labor_law",
        "questions": [
            "قالو ليا ما تبقاش تجي",
            "ما خلصنيش المشغل",
            "طردوني من الخدمة",
            "مخلاونيش ندخل للشركة",
            "منعوني ندخل نخدم",
            "ما قبلونيش نرجع للخدمة",
            "المشغل نقص ليا فالصالير",
            "واش مفتشية الشغل كتدخل فمشكل الأجر",
            "ما مصرحش بيا ف CNSS",
            "ما تصرحتش فالضمان الاجتماعي",
            "وقع ليا حادث داخل الخدمة",
            "تجرحت فالعمل",
            "بغيت شهادة العمل",
            "ما عطاونيش شهادة الشغل",
            "شحال عندي من نهار ديال الكونجي",
            "العطلة السنوية واش كتخلص",
            "مرضت وغيبت شنو خاصني ندير",
            "عندي شهادة طبية",
            "أنا حامل والمشغل بغا يطردني",
            "رجعت من الولادة وما قبلونيش نرجع",
            "شنو الفرق بين CDD و CDI",
            "خدام بلا عقد",
            "بلا كونطرا واش عندي حق",
            "شنو هو préavis",
            "واش كاين préavis ف CDI",
            "بغيت نستاقل",
            "جبروني نكتب استقالة",
            "خدمت ساعات إضافية",
            "السوايع الزايدة واش فيها زيادة فالصالير",
            "شنو هو الخطأ الجسيم",
            "قالو عندي faute grave",
            "محضر الاستماع قبل الطرد",
            "شنو المسطرة قبل الطرد فالشغل",
            "واش عقد الشغل خاصو يكون مكتوب",
            "certificat de travail شنو خاص يكون فيه",
        ],
    },
    {
        "category": "general_labor_boundary",
        "expected_type": "general_conversation",
        "questions": [
            "كيف داير مع العطلة",
            "بغيت نمشي لعطلة مع العائلة",
            "العطلة مع صحابي زوينة",
            "بغيت نرتاح من كلشي",
            "الجو فالشركة ديال القهوة زوين",
            "service dyal café mzyan",
            "chef dyal restaurant كان لطيف",
            "مشيت للبحر بعد الخدمة البارح",
            "خدمت على راسي فالرياضة اليوم",
            "بغيت نصبر شوية ونشوف",
        ],
    },
    {
        "category": "labor_boundary",
        "expected_type": "labor_law",
        "questions": [
            "العطلة السنوية فالشغل شحال فيها",
            "service RH قالو ليا ما تبقاش تجي",
            "chef dyali f service نقص ليا فالصالير",
            "الباطرون قال سير حتى نعيطو ليك",
            "HR ما عطاونيش شهادة العمل",
            "المشغل منعني ندخل نخدم",
            "الشركة ما صرحتش بيا فالضمان",
            "تجرحت فالورشة أثناء الخدمة",
            "بغيت نعرف حقوقي فالأجر",
            "خدام بلا كونطرا فشركة",
        ],
    },
]


UNSAFE_PHRASES = ["نضمن ليك", "أكيد تربح", "غادي تربح"]
LAWYER_CLAIMS = ["أنا محامي", "بصفتي محامي", "كمحامي", "je suis avocat", "i am a lawyer"]
CITATION_RE = re.compile(r"\[المصدر\s+\d+،\s+الصفحة\s+[^\]]+\]")
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def contains_any(text: str, terms: list[str]) -> bool:
    normalized = normalize(text)
    return any(normalize(term) in normalized for term in terms)


def build_cases() -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    seen: set[str] = set()
    for group in CASE_GROUPS:
        category = str(group["category"])
        expected_type = str(group["expected_type"])
        for index, question in enumerate(group["questions"], start=1):
            key = normalize(question)
            if key in seen:
                continue
            seen.add(key)
            cases.append(
                {
                    "id": f"{category}_{index:03d}",
                    "category": category,
                    "question": question,
                    "expected_type": expected_type,
                }
            )
    return cases


def expected_route(expected_type: str) -> str:
    return "labor" if expected_type == "labor_law" else "direct"


def score_case(
    case: dict[str, str],
    classification: dict[str, Any],
    answer: str,
    sources: list[Any],
) -> list[str]:
    failures: list[str] = []
    expected_type = case["expected_type"]
    actual_type = str(classification.get("type"))

    if actual_type != expected_type:
        failures.append(f"classifier expected {expected_type}, got {actual_type}")

    if not answer.strip():
        failures.append("empty answer")
        return failures

    if not ARABIC_RE.search(answer):
        failures.append("answer does not look like Arabic/Darija")

    for phrase in UNSAFE_PHRASES:
        if phrase in answer:
            failures.append(f"unsafe guarantee phrase: {phrase}")
    for phrase in LAWYER_CLAIMS:
        if normalize(phrase) in normalize(answer):
            failures.append(f"pretends to be a lawyer: {phrase}")

    if expected_route(expected_type) == "direct":
        if sources:
            failures.append(f"direct Darija response should not return sources, got {len(sources)}")
        if CITATION_RE.search(answer):
            failures.append("direct Darija response should not include legal citations")
        if expected_type == "non_labor_law_legal":
            if not contains_any(answer, ["خارج تخصصي", "مدونة الشغل", "الخدمة"]):
                failures.append("non-labor legal answer should explain the labor-law boundary")
        elif expected_type == "unknown":
            if not contains_any(answer, ["ما واضحش", "شرح ليا"]):
                failures.append("unknown answer should ask for clarification")
        elif expected_type == "thanks":
            if not contains_any(answer, ["العفو", "مرحبا"]):
                failures.append("thanks answer should acknowledge thanks")
        elif expected_type == "greeting":
            if not contains_any(answer, ["سلام", "مرحبا", "أهلا"]):
                failures.append("greeting answer should greet back")
        elif not contains_any(answer, ["فهم", "الشغل", "مدونة الشغل", "الدارجة"]):
            failures.append("general answer should show Darija comprehension")
    else:
        if len(sources) < 1:
            failures.append(f"labor-law response should return at least one source, got {len(sources)}")
        if not CITATION_RE.search(answer):
            failures.append("labor-law response should include legal citation")
        if not contains_any(
            answer,
            [
                "الشغل",
                "الخدمة",
                "الشركة",
                "المشغل",
                "صاحب العمل",
                "قانون العمل",
                "الأجر",
                "الصالير",
                "العقد",
                "CNSS",
                "الضمان",
                "الفصل",
                "الطرد",
                "العطلة",
                "حادث",
                "مفتشية",
            ],
        ):
            failures.append("labor-law answer missing expected labor-law signal")

    return failures


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_report(
    *,
    cases: list[dict[str, str]],
    results: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    latencies: list[int],
    target: float,
    report_path: Path,
) -> None:
    total = len(results)
    passed = total - len(failures)
    score = passed / total if total else 0.0
    category_counts = Counter(str(result["category"]) for result in results)
    type_counts = Counter(str(result["expected_type"]) for result in results)
    failure_counts = Counter(str(result["category"]) for result in failures)
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else 0
    median_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0
    max_latency = max(latencies) if latencies else 0

    lines = [
        "# Darija Comprehension Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Total cases: {len(cases)}",
        f"- Passed: {passed}",
        f"- Failed: {len(failures)}",
        f"- Pass rate: {score:.1%}",
        f"- Target: {target:.1%}",
        f"- Status: {'PASS' if score >= target else 'FAIL'}",
        f"- Average latency: {avg_latency} ms",
        f"- Median latency: {median_latency} ms",
        f"- Max latency: {max_latency} ms",
        "",
        "## Cases By Category",
        "",
    ]
    for category, count in sorted(category_counts.items()):
        lines.append(f"- {category}: {count}")

    lines.extend(["", "## Cases By Expected Type", ""])
    for expected_type, count in sorted(type_counts.items()):
        lines.append(f"- {expected_type}: {count}")

    lines.extend(["", "## Failures By Category", ""])
    if failure_counts:
        for category, count in sorted(failure_counts.items()):
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "## Failed Examples", ""])
    if failures:
        for failure in failures[:75]:
            joined = "; ".join(failure["failures"])
            lines.append(
                f"- {failure['id']} [{failure['category']}]: {failure['question']} -> {joined}"
            )
        if len(failures) > 75:
            lines.append(f"- ... {len(failures) - 75} more")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- `{RESULTS_PATH.name}`",
            f"- `{FAILURES_PATH.name}`",
            f"- `{report_path.name}`",
            "",
            "## Note",
            "",
            "This evaluates the current live chatbot path and routing. It does not prove a QLoRA adapter, because training has not started.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    global REPORT_PATH

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--target", type=float, default=0.90)
    args = parser.parse_args()
    REPORT_PATH = Path(args.report)

    cases = build_cases()
    if len(cases) < 300:
        raise RuntimeError(f"Expected at least 300 comprehension cases, built {len(cases)}")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    latencies: list[int] = []

    for case in cases:
        print(f"\n[{case['id']}] {case['question']}")
        started = time.perf_counter()
        try:
            classification = classify_conversation(case["question"])
            answer, sources = ask_chatbot(case["question"], return_sources=True)
        except requests.exceptions.ConnectionError:
            print("Ollama is not running on localhost:11434. Start it with: ollama serve")
            return 2
        except requests.exceptions.Timeout:
            print("Ollama timed out while evaluating this case.")
            return 2
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        latencies.append(elapsed_ms)

        case_failures = score_case(case, classification, answer, sources)
        ok = not case_failures
        print("PASS" if ok else "FAIL")
        if case_failures:
            for failure in case_failures:
                print(f"- {failure}")
        print(f"Route: {classification['type']} ({float(classification['confidence']):.2f})")
        print(f"Sources: {len(sources)}")
        print(f"Latency: {elapsed_ms} ms")

        result = {
            **case,
            "actual_type": classification["type"],
            "confidence": float(classification["confidence"]),
            "passed": ok,
            "failures": case_failures,
            "latency_ms": elapsed_ms,
            "answer": answer,
            "sources": [
                {
                    "number": getattr(source, "number", None),
                    "page": getattr(source, "page", None),
                    "distance": getattr(source, "distance", None),
                    "category": getattr(source, "category", None),
                }
                for source in sources
            ],
        }
        results.append(result)
        if not ok:
            failures.append(result)

    write_jsonl(RESULTS_PATH, results)
    write_jsonl(FAILURES_PATH, failures)
    write_report(
        cases=cases,
        results=results,
        failures=failures,
        latencies=latencies,
        target=args.target,
        report_path=REPORT_PATH,
    )

    passed = len(results) - len(failures)
    score = passed / len(results) if results else 0.0
    print(f"\nDarija comprehension score: {passed}/{len(results)} ({score:.1%})")
    print("Status:", "PASS" if score >= args.target else "NEEDS IMPROVEMENT")
    print(f"Report written to {REPORT_PATH}")
    return 0 if score >= args.target else 1


if __name__ == "__main__":
    raise SystemExit(main())
