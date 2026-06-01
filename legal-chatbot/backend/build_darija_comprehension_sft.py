"""Build a broad Moroccan Darija comprehension SFT dataset.

This dataset is separate from the legal-law SFT dataset. It teaches Lmo7ami AI
to recognize broad Darija messages, summarize/interpret them cautiously, and
keep the assistant inside its Moroccan labor-law scope when the topic is not
legal.
"""

from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from download_external_darija import CLEAN_PATH, RAW_DIR, dedupe_key, is_noisy_text, normalize_darija


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data" / "training"
TRAIN_PATH = DATA_DIR / "darija_comprehension_train.jsonl"
VAL_PATH = DATA_DIR / "darija_comprehension_val.jsonl"
TEST_PATH = DATA_DIR / "darija_comprehension_test.jsonl"
MANIFEST_PATH = DATA_DIR / "darija_comprehension_manifest.json"
REPORT_PATH = PROJECT_DIR / "darija_comprehension_training_report.md"

SYSTEM_PROMPT = (
    "أنت Lmo7ami AI، مساعد قانوني مغربي كتهضر بالدارجة المغربية. "
    "فهم رسائل المستخدم بالدارجة حتى إلا كانت خارج القانون، ولكن خليك واضح: "
    "تخصصك هو مدونة الشغل المغربية. ما تدعيش أنك محامي، ما تعطيش ضمانات، "
    "وإلى كان الموضوع خارج نطاق الشغل جاوب بلطف ووجه المستخدم باش يوضح إلا كان عندو مشكل فالشغل."
)

TOTAL_EXAMPLES = 10000
TRAIN_COUNT = 8000
VAL_COUNT = 1000
TEST_COUNT = 1000
SEED = 20260531

LEGAL_HINTS = (
    "خدمة",
    "الشغل",
    "لخدمة",
    "الخدمة",
    "مشغل",
    "patron",
    "salaire",
    "صالير",
    "طرد",
    "كونطرا",
    "contrat",
    "cnss",
)
URL_OR_CONTACT_RE = re.compile(r"https?://|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE)


@dataclass(frozen=True)
class DodaPair:
    darija: str
    gloss: str
    raw_ref: str
    row_index: int
    field: str


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def safe_text(value: Any) -> str:
    return normalize_darija(str(value)) if value is not None else ""


def has_legal_hint(text: str) -> bool:
    lowered = text.casefold()
    return any(hint.casefold() in lowered for hint in LEGAL_HINTS)


def clean_gloss(value: Any) -> str:
    gloss = safe_text(value)
    if not gloss:
        return ""
    if len(gloss) < 2 or len(gloss) > 300:
        return ""
    if URL_OR_CONTACT_RE.search(gloss):
        return ""
    return gloss


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return []

    header = [cell.strip() for cell in rows[0]]
    has_header = any(cell.casefold() in {"darija", "darija_ar", "eng"} for cell in header)
    field_names = header if has_header else [f"col_{index}" for index in range(1, len(rows[0]) + 1)]
    data_rows = rows[1:] if has_header else rows

    result: list[dict[str, str]] = []
    for row in data_rows:
        result.append(
            {
                field_names[index] if index < len(field_names) else f"col_{index + 1}": value
                for index, value in enumerate(row)
            }
        )
    return result


def darija_fields(row: dict[str, str]) -> list[tuple[str, str]]:
    preferred_fields = ("darija", "darija_ar")
    fields: list[tuple[str, str]] = []
    for field_name in preferred_fields:
        value = safe_text(row.get(field_name))
        if value and not is_noisy_text(value):
            fields.append((field_name, value))

    if fields:
        return fields

    for field_name, value in row.items():
        lowered = field_name.casefold()
        if lowered in {"eng", "english", "fr", "french"}:
            continue
        text = safe_text(value)
        if text and not is_noisy_text(text):
            fields.append((field_name, text))
    return fields


def load_doda_pairs() -> list[DodaPair]:
    pairs: list[DodaPair] = []
    doda_dir = RAW_DIR / "doda"
    if not doda_dir.exists():
        return pairs

    seen: set[str] = set()
    for path in sorted(doda_dir.rglob("*.csv")):
        raw_ref = path.relative_to(PROJECT_DIR).as_posix()
        for row_index, row in enumerate(csv_rows(path), start=1):
            gloss = clean_gloss(row.get("eng") or row.get("english") or "")
            for field_name, text in darija_fields(row):
                key = dedupe_key(text)
                if key in seen:
                    continue
                seen.add(key)
                pairs.append(
                    DodaPair(
                        darija=text,
                        gloss=gloss,
                        raw_ref=raw_ref,
                        row_index=row_index,
                        field=field_name,
                    )
                )
    return pairs


def load_external_texts() -> list[DodaPair]:
    pairs = load_doda_pairs()
    if pairs:
        return pairs

    fallback: list[DodaPair] = []
    for index, row in enumerate(read_jsonl(CLEAN_PATH), start=1):
        text = safe_text(row.get("text"))
        if not text or is_noisy_text(text):
            continue
        source = row.get("source", {}) if isinstance(row.get("source"), dict) else {}
        fallback.append(
            DodaPair(
                darija=text,
                gloss="",
                raw_ref=str(source.get("raw_ref", CLEAN_PATH.relative_to(PROJECT_DIR).as_posix())),
                row_index=int(source.get("row_index", index) or index),
                field=str(source.get("field", "text")),
            )
        )
    return fallback


def make_user(pair: DodaPair, index: int) -> str:
    templates = (
        "{text}",
        "شنو كتعني هاد الجملة: {text}",
        "فهمني هاد الدارجة: {text}",
        "wach fhemtini ila gelt lik: {text}",
        "هادشي بالدارجة واش تقدر تفهمو: {text}",
    )
    return templates[index % len(templates)].format(text=pair.darija)


def make_assistant(pair: DodaPair, index: int) -> str:
    boundary = (
        "إلى كان هاد الكلام مرتبط بمشكل فالشغل فالمغرب، زيد شرح ليا الوقائع والوثائق اللي عندك. "
        "إلى كان خارج مدونة الشغل، نقدر غير نفهم المعنى العام وما نعطيش توجيه متخصص خارج النطاق."
    )
    if pair.gloss:
        templates = (
            "فهمت الرسالة بالدارجة. المعنى التقريبي هو: {gloss}. {boundary}",
            "هاد العبارة كتقرب لمعنى: {gloss}. {boundary}",
            "نقدر نفهمها على أنها: {gloss}. {boundary}",
        )
        return templates[index % len(templates)].format(gloss=pair.gloss, boundary=boundary)

    if has_legal_hint(pair.darija):
        return (
            "فهمت من كلامك أنه ممكن يكون مرتبط بالخدمة أو الشغل. باش نعطيك توجيه مضبوط، "
            "وضح ليا شنو وقع، واش كاين عقد أو وثائق، وشنو بغيتي تعرف بالضبط. "
            "هادشي توجيه عام وماشي استشارة قانونية رسمية."
        )

    return (
        "فهمت الرسالة بالدارجة، ولكن ما بايناش سؤال واضح فمدونة الشغل. "
        "إلى كان عندك مشكل فالأجر، الطرد، العقد، CNSS، العطلة، أو حادثة شغل، شرح ليا السياق. "
        "إلى كان الموضوع خارج الشغل، ما نقدرش نعطيك جواب متخصص خارج نطاقي."
    )


def make_record(pair: DodaPair, index: int, mode: str) -> dict[str, Any]:
    user = make_user(pair, index)
    assistant = make_assistant(pair, index)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": {
            "intent": "broad_darija_comprehension",
            "topic": "darija_comprehension",
            "mode": mode,
            "source": "doda_external",
            "raw_ref": pair.raw_ref,
            "row_index": pair.row_index,
            "field": pair.field,
            "requires_rag": False,
            "legal_dataset": False,
            "quality": "external_cleaned",
        },
    }


def build_records() -> list[dict[str, Any]]:
    pairs = load_external_texts()
    if len(pairs) < TOTAL_EXAMPLES:
        raise RuntimeError(
            f"Need at least {TOTAL_EXAMPLES} external Darija examples, found {len(pairs)}. "
            "Run download_external_darija.py first."
        )

    rng = random.Random(SEED)
    rng.shuffle(pairs)
    records: list[dict[str, Any]] = []
    seen_users: set[str] = set()

    for index, pair in enumerate(pairs):
        mode = "meaning_with_boundary" if pair.gloss else "scope_router"
        record = make_record(pair, index, mode)
        user = record["messages"][1]["content"]
        key = dedupe_key(user)
        if key in seen_users:
            continue
        seen_users.add(key)
        records.append(record)
        if len(records) >= TOTAL_EXAMPLES:
            break

    if len(records) != TOTAL_EXAMPLES:
        raise RuntimeError(f"Expected {TOTAL_EXAMPLES} records, built {len(records)}")
    return records


def split_records(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(SEED)
    shuffled = list(records)
    rng.shuffle(shuffled)
    splits = {
        "train": shuffled[:TRAIN_COUNT],
        "val": shuffled[TRAIN_COUNT : TRAIN_COUNT + VAL_COUNT],
        "test": shuffled[TRAIN_COUNT + VAL_COUNT :],
    }
    for split, rows in splits.items():
        for index, row in enumerate(rows, start=1):
            row["metadata"]["split"] = split
            row["metadata"]["example_id"] = f"lmo7ami-darija-{split}-{index:05d}"
    return splits


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_manifest(splits: dict[str, list[dict[str, Any]]]) -> None:
    all_rows = [row for rows in splits.values() for row in rows]
    mode_counts = Counter(row["metadata"]["mode"] for row in all_rows)
    manifest = {
        "name": "Lmo7ami broad Moroccan Darija comprehension SFT dataset",
        "version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "backend/build_darija_comprehension_sft.py",
        "source": "data/external_darija/clean_darija_examples.jsonl and raw DODa CSV files",
        "purpose": "Improve broad Moroccan Darija understanding and off-topic routing without memorizing law.",
        "total_examples": len(all_rows),
        "splits": {
            "train": {"path": "data/training/darija_comprehension_train.jsonl", "count": len(splits["train"])},
            "validation": {"path": "data/training/darija_comprehension_val.jsonl", "count": len(splits["val"])},
            "test": {"path": "data/training/darija_comprehension_test.jsonl", "count": len(splits["test"])},
        },
        "mode_counts": dict(sorted(mode_counts.items())),
        "guardrails": [
            "This dataset is not a legal fact dataset.",
            "The assistant remains scoped to Moroccan labor law for specialized guidance.",
            "Legal facts, citations, and law-specific answers must still come from RAG.",
            "No training should replace refusal, clarification, or source-grounding behavior.",
        ],
        "system_prompt": SYSTEM_PROMPT,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(splits: dict[str, list[dict[str, Any]]]) -> None:
    all_rows = [row for rows in splits.values() for row in rows]
    mode_counts = Counter(row["metadata"]["mode"] for row in all_rows)
    raw_counts = Counter(row["metadata"]["raw_ref"] for row in all_rows)
    lines = [
        "# Darija Comprehension Training Dataset Report",
        "",
        "## Summary",
        "",
        f"- Total examples: {len(all_rows)}",
        f"- Train examples: {len(splits['train'])}",
        f"- Validation examples: {len(splits['val'])}",
        f"- Test examples: {len(splits['test'])}",
        "- Legal facts included: no",
        "- Mixed into legal SFT dataset: no",
        "",
        "## Examples Per Mode",
        "",
    ]
    for mode, count in sorted(mode_counts.items()):
        lines.append(f"- {mode}: {count}")

    lines.extend(["", "## Top Raw Sources", ""])
    for raw_ref, count in raw_counts.most_common(10):
        lines.append(f"- `{raw_ref}`: {count}")

    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            "Run `python train_darija_qlora.py --preflight` from `backend/`. "
            "Only start real QLoRA after the ML stack and GPU target are confirmed.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    records = build_records()
    splits = split_records(records)
    write_jsonl(TRAIN_PATH, splits["train"])
    write_jsonl(VAL_PATH, splits["val"])
    write_jsonl(TEST_PATH, splits["test"])
    write_manifest(splits)
    write_report(splits)

    print("Darija comprehension SFT dataset")
    print(f"- train: {len(splits['train'])} -> {TRAIN_PATH.relative_to(PROJECT_DIR).as_posix()}")
    print(f"- val: {len(splits['val'])} -> {VAL_PATH.relative_to(PROJECT_DIR).as_posix()}")
    print(f"- test: {len(splits['test'])} -> {TEST_PATH.relative_to(PROJECT_DIR).as_posix()}")
    print(f"- manifest: {MANIFEST_PATH.relative_to(PROJECT_DIR).as_posix()}")
    print(f"- report: {REPORT_PATH.relative_to(PROJECT_DIR).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
