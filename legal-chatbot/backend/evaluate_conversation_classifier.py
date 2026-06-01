# -*- coding: utf-8 -*-
"""Evaluate the pre-RAG conversation classifier.

The target is to keep general Darija out of the labor-law RAG pipeline while
preserving routing for real Moroccan labor-law questions.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from conversation_classifier import classify_conversation


BASE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = BASE_DIR / "conversation_classifier_results.jsonl"
FAILURES_PATH = BASE_DIR / "conversation_classifier_failures.jsonl"
REPORT_PATH = BASE_DIR / "conversation_classifier_report.md"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


CASE_GROUPS: dict[str, dict[str, list[str]]] = {
    "greeting": {
        "greeting": [
            "السلام عليكم",
            "سلام",
            "السلام",
            "salam",
            "salam alikom",
            "salam alaikom",
            "bonjour",
            "hello",
            "hi",
            "صباح الخير",
            "مسا الخير",
            "ahlan",
            "labas",
            "سلام عليكم خويا",
            "salam khoya",
        ]
    },
    "thanks": {
        "thanks": [
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
        ]
    },
    "general_conversation": {
        "smalltalk": [
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
            "شنو رأيك فالدّارجة المغربية",
            "كتعرف مراكش",
            "بغيت نضحك شوية",
            "راه الجو مزيان",
        ],
        "emotions": [
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
        ],
        "daily_life": [
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
        ],
        "explanations": [
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
        ],
        "mixed_french_darija": [
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
        ],
        "arabizi": [
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
        ],
    },
    "labor_law": {
        "labor_law": [
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
            "عندي عقد محدد المدة وبقى مستمر",
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
            "proof ديال relation de travail شنو ممكن يكون",
            "certificat de travail شنو خاص يكون فيه",
            "congé annuel payé شنو هو",
            "heures supplémentaires فمدونة الشغل شنو هي",
            "accident de travail فالشركة شنو خاص يتدار",
            "ما مسجلنيش فالصندوق الوطني للضمان الاجتماعي",
            "الأجر تأخر بزاف",
            "الخلاص ديالي بقا عند الشركة",
            "خدمت أكثر من الوقت العادي",
            "شهادة طبية خاصها تتعطى للمشغل فوقاش",
            "المشغل بغا يدير فحص مضاد فالمرض",
            "مدة الإخطار قبل الطرد شنو هي",
            "indemnité de préavis شنو معناها",
            "واش يمكن إثبات عقد الشغل بجميع الوسائل",
            "المشغل ما عطانيش شهادة الشغل",
        ],
    },
    "non_labor_law_legal": {
        "non_labor_law_legal": [
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
            "محكمة تجارية فاش كتعاون",
            "عندي نزاع مع مول الدار",
            "بغيت نبدل الحالة المدنية",
            "عندي قضية جنائية",
            "شنو ندير فميراث الوالد",
        ],
    },
    "unknown": {
        "unknown": [
            "؟؟؟",
            "...",
            "!!!",
            "   ",
            "؟؟؟؟؟؟",
            "----",
            "::::",
            "، ، ،",
            "???",
            "......",
        ]
    },
}


def build_cases() -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    seen: set[str] = set()
    for expected_type, groups in CASE_GROUPS.items():
        for coverage, questions in groups.items():
            for index, question in enumerate(questions, start=1):
                key = " ".join(question.split()).casefold()
                if key in seen:
                    continue
                seen.add(key)
                cases.append(
                    {
                        "id": f"{coverage}_{index:03d}",
                        "coverage": coverage,
                        "question": question,
                        "expected_type": expected_type,
                    }
                )
    return cases


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_report(
    *,
    cases: list[dict[str, str]],
    results: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    target: float,
    report_path: Path,
) -> None:
    passed = len(results) - len(failures)
    accuracy = passed / len(results) if results else 0.0
    by_expected = Counter(result["expected_type"] for result in results)
    failures_by_expected = Counter(result["expected_type"] for result in failures)
    by_coverage = Counter(result["coverage"] for result in results)

    lines = [
        "# Conversation Classifier Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Total cases: {len(cases)}",
        f"- Passed: {passed}",
        f"- Failed: {len(failures)}",
        f"- Accuracy: {accuracy:.1%}",
        f"- Target: {target:.1%}",
        f"- Status: {'PASS' if accuracy >= target else 'FAIL'}",
        "",
        "## Cases By Expected Type",
        "",
    ]
    for expected_type, count in sorted(by_expected.items()):
        lines.append(f"- {expected_type}: {count}")

    lines.extend(["", "## Cases By Coverage", ""])
    for coverage, count in sorted(by_coverage.items()):
        lines.append(f"- {coverage}: {count}")

    lines.extend(["", "## Failures By Expected Type", ""])
    if failures_by_expected:
        for expected_type, count in sorted(failures_by_expected.items()):
            lines.append(f"- {expected_type}: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "## Failed Examples", ""])
    if failures:
        for failure in failures[:50]:
            lines.append(
                f"- {failure['id']} [{failure['coverage']}]: expected={failure['expected_type']} "
                f"actual={failure['actual_type']} confidence={failure['confidence']:.2f} "
                f"question={failure['question']}"
            )
        if len(failures) > 50:
            lines.append(f"- ... {len(failures) - 50} more")
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
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=float, default=0.95)
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args()

    cases = build_cases()
    if len(cases) < 200:
        raise RuntimeError(f"Expected at least 200 classifier cases, built {len(cases)}")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for case in cases:
        result = classify_conversation(case["question"])
        actual_type = result["type"]
        ok = actual_type == case["expected_type"]
        row = {
            **case,
            "actual_type": actual_type,
            "confidence": float(result["confidence"]),
            "passed": ok,
        }
        results.append(row)
        if not ok:
            failures.append(row)

    write_jsonl(RESULTS_PATH, results)
    write_jsonl(FAILURES_PATH, failures)
    report_path = Path(args.report)
    write_report(
        cases=cases,
        results=results,
        failures=failures,
        target=args.target,
        report_path=report_path,
    )

    passed = len(results) - len(failures)
    accuracy = passed / len(results) if results else 0.0
    print("Conversation classifier evaluation")
    print(f"- cases: {len(results)}")
    print(f"- passed: {passed}")
    print(f"- failed: {len(failures)}")
    print(f"- accuracy: {accuracy:.1%}")
    print(f"- target: {args.target:.1%}")
    print("Status:", "PASS" if accuracy >= args.target else "FAIL")
    if failures:
        print("Failures:")
        for failure in failures[:25]:
            print(
                f"- {failure['id']}: expected={failure['expected_type']} "
                f"actual={failure['actual_type']} question={failure['question']}"
            )
    print(f"Report written to {report_path}")
    return 0 if accuracy >= args.target else 1


if __name__ == "__main__":
    raise SystemExit(main())
