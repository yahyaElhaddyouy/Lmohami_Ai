import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from rag import INSUFFICIENT_CONTEXT_MESSAGE, ask_chatbot

QUESTIONS = [
    "شنو الحقوق ديالي إلا طردوني من الخدمة بلا إنذار؟",
    "شحال عندي من نهار ديال الكونجي السنوي فمدونة الشغل؟",
    "واش المشغل يقدر ينقص ليا فالصالير بلا موافقتي؟",
    "شنو خاص يدير المشغل قبل ما يفصل أجير بسبب خطأ جسيم؟",
    "إلا خدمت عامين وتطردت، واش عندي تعويض؟",
    "شنو هو préavis فمدونة الشغل؟",
    "واش يمكن نخدم أكثر من 44 ساعة فالسيمانة؟",
    "شنو الحقوق ديال المرأة الحامل فالخدمة؟",
    "واش عندي الحق نغيب باش نقلب على خدمة خلال مدة الإنذار؟",
    "شنو الفرق بين الاستقالة والطرد؟",
    "واش العطلة السنوية كتضيع إلا ماخديتهاش؟",
    "شنو كتنص عليه المادة 231؟",
    "شنو كتنص عليه المادة 62؟",
    "شنو كتنص عليه المادة 999 من مدونة الشغل؟",
    "واش المشغل يقدر يطردني بلا يسمع ليا؟",
    "شنو خاص يكون فمحضر الاستماع قبل الطرد؟",
    "واش الأجير أقل من 18 عام عندو نفس مدة العطلة السنوية؟",
    "إلا تسدات الشركة مؤقتا واش كنخلص الكونجي؟",
    "واش يمكن نتنازل مسبقا على العطلة السنوية ديالي؟",
    "شنو هو التعويض عن الفصل؟",
    "كيفاش كيتحسب التعويض عن الفصل؟",
    "إلا كان خطأ جسيم واش كاين préavis؟",
    "واش عندي الحق فتعويض إلا كان الطرد تأديبي؟",
    "شنو العقوبات على المشغل إلا ماحترمش العطلة السنوية؟",
    "واش المرض كيتحسب من الكونجي السنوي؟",
    "شنو هي مدة الخدمة المستمرة فالعطلة السنوية؟",
    "شنو يدير الأجير إلا ماخلصوهش؟",
    "واش المشغل يقدر يبدل ليا وقت العمل؟",
    "شنو الحد الأقصى ديال ساعات العمل؟",
    "واش الساعات الإضافية خاصها تخلص؟",
    "شنو الحقوق ديالي إلا وقع ليا حادث شغل؟",
    "بغيت نعرف شنو ندير فحادثة سير فالطريق العام؟",
    "كيفاش ندير طلاق اتفاقي؟",
    "شنو ندير إلا كريت دار ومول الدار بغا يخرجني؟",
    "واش نقدر نرفع دعوى تجارية على شركة؟",
    "شنو هي حقوق الأجير فالعطلة ديال الولادة؟",
    "واش النقابة عندها دور فالشركة؟",
    "شنو هو ممثل الأجراء؟",
    "واش خاص النظام الداخلي فكل شركة؟",
    "إلا رفضت نوقع على محضر الاستماع شنو كيوقع؟",
    "شنو الوثائق اللي خاصني نجمع إلا تطردت؟",
    "واش يمكن للمشغل يمنعني من الكونجي؟",
    "واش العطل الرسمية كتزاد على الكونجي السنوي؟",
    "شنو معنى jours de travail effectif؟",
    "واش الكونجي يمكن يتقسم على جوج سنين؟",
    "شنو كتنص عليه المادة 240؟",
    "شنو كتنص عليه المادة 242؟",
    "شنو كتنص عليه المادة 247؟",
    "واش خاص المشغل يخبر مفتش الشغل فشي حالات؟",
    "شنو دور مفتش الشغل فالنزاعات؟",
    "شنو ندير إلا خدموني بلا عقد مكتوب؟",
    "واش CDD يقدر يتحول CDI؟",
    "شنو الفرق بين CDD و CDI؟",
    "إلا سالا الكونترا ديال CDD واش كاين تعويض؟",
    "واش فترة التجربة فيها préavis؟",
    "شنو هي الأخطاء الجسيمة؟",
    "واش السب والشتم يقدر يكون خطأ جسيم؟",
    "واش التغيب بلا مبرر يقدر يسبب الطرد؟",
    "شنو يدير الأجير إلا ما تصرحش ف CNSS؟",
    "واش هاد البوت يقدر يعطيني استشارة قانونية نهائية؟",
]

OUT_OF_SCOPE_MARKERS = [
    "حادثة سير",
    "طلاق",
    "كريت دار",
    "تجارية",
]


def has_citation(answer: str) -> bool:
    return "[المصدر " in answer and "الصفحة" in answer


def expected_refusal(question: str) -> bool:
    return any(marker in question for marker in OUT_OF_SCOPE_MARKERS)


def grade(question: str, answer: str, source_count: int) -> list[str]:
    failures = []
    refused = INSUFFICIENT_CONTEXT_MESSAGE in answer or "خارج" in answer or "محدود" in answer

    if expected_refusal(question):
        if not refused:
            failures.append("expected refusal for out-of-scope question")
    elif source_count > 0 and not refused and not has_citation(answer):
        failures.append("missing citation")

    unsafe_phrases = [
        "نضمن",
        "أكيد تربح",
        "خاصك دير شكاية",
        "art 1365",
        "المادة 1365",
    ]
    for phrase in unsafe_phrases:
        if phrase in answer:
            failures.append(f"unsafe phrase: {phrase}")

    return failures


def append_jsonl(path: Path, item: dict):
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Ask the chatbot questions for a fixed duration.")
    parser.add_argument("--minutes", type=float, default=30)
    parser.add_argument("--report", default="stress_report.jsonl")
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    report_path = Path(args.report)
    deadline = time.monotonic() + (args.minutes * 60)
    index = 0
    passed = 0
    failed = 0

    append_jsonl(
        report_path,
        {
            "event": "start",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "minutes": args.minutes,
            "question_count": len(QUESTIONS),
        },
    )

    while time.monotonic() < deadline:
        question = QUESTIONS[index % len(QUESTIONS)]
        started = time.monotonic()
        record = {
            "event": "question",
            "number": index + 1,
            "question": question,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            answer, sources = ask_chatbot(question, return_sources=True)
            failures = grade(question, answer, len(sources))
            record.update(
                {
                    "passed": not failures,
                    "failures": failures,
                    "answer": answer,
                    "sources": [
                        {
                            "number": source.number,
                            "page": source.page,
                            "distance": source.distance,
                        }
                        for source in sources
                    ],
                }
            )
            if failures:
                failed += 1
            else:
                passed += 1
        except Exception as exc:
            failed += 1
            record.update(
                {
                    "passed": False,
                    "failures": [f"exception: {exc}"],
                    "answer": "",
                    "sources": [],
                }
            )

        record["duration_seconds"] = round(time.monotonic() - started, 2)
        append_jsonl(report_path, record)

        index += 1
        time.sleep(args.sleep)

    append_jsonl(
        report_path,
        {
            "event": "finish",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "asked": index,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / index if index else 0,
        },
    )


if __name__ == "__main__":
    main()
