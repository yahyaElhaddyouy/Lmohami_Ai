"""Generate Moroccan Darija labor-law intent paraphrases.

The output is JSONL with instruction/input/output fields so it can be merged
directly into a supervised fine-tuning dataset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


INSTRUCTION = (
    "صنف سؤال المستخدم المغربي بالدارجة حول قانون الشغل المغربي. "
    "جاوب فقط باسم النية القانونية المناسبة."
)


INTENT_SEEDS = {
    "dismissal": {
        "formal": [
            "تم فصلي من العمل بدون توضيح السبب، شنو يمكن ندير؟",
            "المشغل أنهى علاقة الشغل معايا بلا إشعار مكتوب.",
        ],
        "slang": [
            "طردوني",
            "حبسوني",
            "خرجوني",
            "قالو ليا ما تبقاش تجي",
        ],
        "short": ["طرد من الخدمة؟", "خرجوني شنو ندير؟"],
        "mixed_fr": ["دارو ليا licenciement بلا motif", "patron قال ليا stop service"],
        "typo": ["طردوني من الخدمه", "خرجووني بلا سبب"],
        "angry": ["هادشي ظلم طردوني بلا حتى ورقة!", "واش يعقل يخرجوني هكاك؟"],
        "vague": ["وقع ليا مشكل مع الخدمة وبقيت فالدار", "ما بقاش خدام عندهم وما فهمتش علاش"],
    },
    "salary": {
        "formal": [
            "لم أتوصل بالأجر ديالي فالأجل المعتاد.",
            "المشغل تأخر عليا فالأداء ديال الصالير.",
        ],
        "slang": ["ما عطانيش الصالير", "خلصوني ناقص", "باقي ما شفت والو"],
        "short": ["فين الصالير؟", "ما خلصونيش؟"],
        "mixed_fr": ["salaire ديالي باقي ما خرجش", "retard paiement salaire شنو ندير؟"],
        "typo": ["ما عطاونيش صالير", "خلصوني ناقيص"],
        "angry": ["خدمت الشهر كامل وما خلصونيش!", "واش باغيين ياكلو ليا عرقي؟"],
        "vague": ["عندي مشكل فالفلوس مع الخدمة", "الحساب ديالي ما جا صحيح"],
    },
    "CNSS": {
        "formal": [
            "بغيت نعرف واش المشغل مصرح بيا فالصندوق الوطني للضمان الاجتماعي.",
            "ما لقيتش التصريح ديالي ف CNSS.",
        ],
        "slang": ["ما مصرحش بيا", "cnss ما كايناش", "ما دايرش ليا الضمان"],
        "short": ["CNSS؟", "مصرح بيا؟"],
        "mixed_fr": ["declaration CNSS ما كايناش", "patron ما دارش affiliation"],
        "typo": ["cnss ما مصرش بيا", "سي ان اس اس ماكايناش"],
        "angry": ["سنين خدام وما مصرحش بيا ف CNSS!", "ضحك عليا فالضمان الاجتماعي"],
        "vague": ["بغيت نشوف واش حقوقي الاجتماعية دايرة", "كاين شي مشكل فالضمان"],
    },
    "annual_leave": {
        "formal": [
            "طلبت العطلة السنوية المؤدى عنها وتم رفض الطلب.",
            "بغيت نعرف حقي فالعطلة السنوية.",
        ],
        "slang": ["رفضو ليا الكونجي", "ما بغاوش يعطيو ليا كونجي", "بغيت الكونجي ديالي"],
        "short": ["كونجي؟", "العطلة السنوية شحال؟"],
        "mixed_fr": ["conge annuel refusé", "vacances payees ديالي"],
        "typo": ["رفضو ليا الكونجيي", "بغيت كونجي سنوي"],
        "angry": ["عام كامل خدام وما عطاونيش الكونجي!", "حرموني من العطلة ديالي"],
        "vague": ["بغيت نرتاح شوية وما خلاونيش", "عندي مشكل فالعطلة"],
    },
    "work_accidents": {
        "formal": [
            "تعرضت لحادث أثناء العمل وبغيت نعرف الإجراءات.",
            "وقعت ليا إصابة داخل مقر العمل.",
        ],
        "slang": ["طحت فالخدمة", "تكسرت فالخدمة", "ضربتني ماكينة فالخدمة"],
        "short": ["حادث خدمة؟", "تصبت فالخدمة؟"],
        "mixed_fr": ["accident de travail وقع ليا", "certificat medical عندي من service"],
        "typo": ["حاديت فالخدمة", "طحت فالخدمه"],
        "angry": ["تجرحت فالخدمة وبغاو يسكتوني!", "وقع ليا حادث وما عاونونيش"],
        "vague": ["وقع ليا شي حاجة فالخدمة", "تضررت وأنا خدام"],
    },
    "maternity": {
        "formal": [
            "أنا حاملة وبغيت نعرف حقوقي فالشغل.",
            "بغيت معلومات على رخصة الولادة والأجر خلال هاد الفترة.",
        ],
        "slang": ["حاملة وخايفة يخرجوني", "بغيت كونجي ديال الولادة", "أنا حبلى فالخدمة"],
        "short": ["رخصة الولادة؟", "حاملة شنو حقي؟"],
        "mixed_fr": ["conge maternité شحال؟", "grossesse فالخدمة و patron مضايقني"],
        "typo": ["كونجي ماترنيتي", "رخصت الولادة"],
        "angry": ["مني عرفو حاملة بداو كيضايقوني!", "باغيين يخرجوني حيت حبلى"],
        "vague": ["عندي ظرف صحي ونسائي فالخدمة", "قربت نولد وما عارفاش شنو ندير"],
    },
    "contracts": {
        "formal": [
            "أشتغل بدون عقد مكتوب وبغيت نعرف وضعيتي القانونية.",
            "العقد ديالي ما عطاونيش نسخة منو.",
        ],
        "slang": ["خدام بلا كونطرا", "ما عنديش عقد", "كونطرا ما كايناش"],
        "short": ["بلا عقد؟", "فين الكونطرا؟"],
        "mixed_fr": ["contrat ما وقعتوش", "CDI ولا CDD ما فاهم والو"],
        "typo": ["خدام بلا كونترا", "ماعنديش الكونطرات"],
        "angry": ["سنين خدام وبلا عقد!", "ضحكو عليا وما داروش ليا كونطرا"],
        "vague": ["ما عارفش الوضعية ديالي فالشركة", "الأوراق ديال الخدمة ناقصين"],
    },
    "overtime": {
        "formal": [
            "كنخدم ساعات إضافية وما كيتخلصوش ليا.",
            "بغيت نعرف كيفاش كتتحسب الساعات الإضافية.",
        ],
        "slang": ["كيخدموني زيادة", "السوايع الزايدة ما خلصوهاش", "خدام الليل بلا زيادة"],
        "short": ["سوايع زيادة؟", "overtime؟"],
        "mixed_fr": ["heures sup ما خلصونيش", "overtime بلا compensation"],
        "typo": ["الساعات الاضافيه", "خدمت سوايع زايده"],
        "angry": ["كيعصروني بسوايع زيادة بلا خلاص!", "كل نهار كنزيد وما كاين والو"],
        "vague": ["كنبقى بزاف فالشركة", "الوقت ديال الخدمة زايد عليا"],
    },
    "certificates": {
        "formal": [
            "طلبت شهادة العمل والمشغل رفض يعطيني إياها.",
            "بغيت شهادة تثبت أنني كنت خدام فالشركة.",
        ],
        "slang": ["ما بغاوش يعطوني شهادة العمل", "بغيت attestation de travail", "ورقة الخدمة رفضوها"],
        "short": ["شهادة العمل؟", "attestation؟"],
        "mixed_fr": ["certificat de travail ما عطاونيش", "attestation ديال service"],
        "typo": ["شهاده العمل", "اتستاسيون ديال الخدمة"],
        "angry": ["خرجت وما بغاوش يعطوني حتى شهادة!", "حابسيني بورقة الخدمة"],
        "vague": ["خاصني ورقة من الشركة", "بغيت وثيقة تثبت الخدمة"],
    },
    "resignation": {
        "formal": [
            "بغيت نقدم الاستقالة ونفهم الآثار ديالها.",
            "وقعت على استقالة وبغيت نعرف واش كانت صحيحة.",
        ],
        "slang": ["بغيت نخرج بوحدي", "كتبت استقالة", "درت demission"],
        "short": ["استقالة؟", "نخرج من الخدمة؟"],
        "mixed_fr": ["demission واش خاص préavis؟", "resignation تحت الضغط"],
        "typo": ["استقاله", "ديميسيون"],
        "angry": ["ضغطو عليا نوقع الاستقالة!", "خلوني نكتب demission بالغصب"],
        "vague": ["بغيت نسالي معهم", "ما بقيتش قادر نكمل"],
    },
    "disciplinary_procedures": {
        "formal": [
            "توصلت باستدعاء للاستماع التأديبي وبغيت نعرف المسطرة.",
            "المشغل دار ليا عقوبة تأديبية.",
        ],
        "slang": ["عيطو ليا لمجلس تأديبي", "دارو ليا avertissement", "بغاو يعاقبوني فالخدمة"],
        "short": ["مجلس تأديبي؟", "إنذار فالخدمة؟"],
        "mixed_fr": ["procedure disciplinaire شنو هي؟", "avertissement من RH"],
        "typo": ["مسطره تاديبيه", "انذار فالخدمه"],
        "angry": ["لفقو ليا مخالفة وبغاو يعاقبوني!", "كيهددوني بعقوبة بلا سبب"],
        "vague": ["عندي مشكل مع الإدارة", "وصلاتني ورقة من الموارد البشرية"],
    },
}


def iter_records() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for intent, groups in INTENT_SEEDS.items():
        for examples in groups.values():
            for text in examples:
                normalized = " ".join(text.split())
                if normalized in seen:
                    continue
                seen.add(normalized)
                records.append(
                    {
                        "instruction": INSTRUCTION,
                        "input": normalized,
                        "output": intent,
                    }
                )
    return records


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="data/synthetic/darija_labor_intents.jsonl",
        help="Path for generated JSONL paraphrases.",
    )
    args = parser.parse_args()

    records = iter_records()
    write_jsonl(Path(args.output), records)
    print(f"Wrote {len(records)} paraphrases to {args.output}")


if __name__ == "__main__":
    main()
