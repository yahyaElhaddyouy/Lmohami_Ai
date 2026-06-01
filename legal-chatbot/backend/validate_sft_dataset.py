"""Validate the Lmo7ami AI SFT dataset for safety and split integrity."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "training"
TRAIN_PATH = DATA_DIR / "lmo7ami_sft_train.jsonl"
VAL_PATH = DATA_DIR / "lmo7ami_sft_val.jsonl"
TEST_PATH = DATA_DIR / "lmo7ami_sft_test.jsonl"
MANIFEST_PATH = DATA_DIR / "dataset_manifest.json"

SPLIT_PATHS = {
    "train": TRAIN_PATH,
    "val": VAL_PATH,
    "test": TEST_PATH,
}

EXPECTED_SPLIT_COUNTS = {
    "train": 1200,
    "val": 150,
    "test": 150,
}

REQUIRED_TOPICS = [
    "greetings_identity",
    "unclear_question",
    "dismissal",
    "disciplinary_dismissal",
    "salary_unpaid",
    "salary_deduction",
    "cnss_non_declaration",
    "work_accident",
    "annual_leave",
    "sick_leave",
    "maternity_protection",
    "contract_type",
    "no_written_contract",
    "work_certificate",
    "preavis",
    "resignation",
    "overtime",
    "out_of_scope_refusal",
    "fake_article_refusal",
    "legal_guarantee_refusal",
    "clarification_questions",
    "practical_steps",
]

UNSAFE_PHRASES = [
    "نضمن ليك",
    "أكيد تربح",
    "غادي تربح",
]

DISCLAIMER_MARKERS = [
    "ماشي استشارة قانونية رسمية",
    "للتوجيه العام",
    "توجيه عام",
    "توجيه أولي",
    "للتوجيه فقط",
]

FAKE_ARTICLE_PATTERNS = [
    re.compile(r"\barticle\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bart\.?\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bloi\s+n?[°o]?\s*\d+\b", re.IGNORECASE),
    re.compile(r"الفصل\s+\d+"),
    re.compile(r"المادة\s+\d+"),
    re.compile(r"القانون\s+رقم\s+\d+"),
]

PII_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE),
    re.compile(r"\b(?:\+?212|0)[5-7]\d{8}\b"),
    re.compile(r"\b[A-Z]{1,2}\d{5,}\b", re.IGNORECASE),
]

PRETEND_LAWYER_PHRASES = [
    "أنا محامي",
    "بصفتي محامي",
    "كمحامي",
    "je suis avocat",
    "i am a lawyer",
]


def normalize_text(text: str) -> str:
    return " ".join(text.split()).casefold()


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return rows, [f"{path}: file does not exist"]

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{line_number}: invalid JSONL: {exc}")
                continue
            row["_line"] = line_number
            row["_file"] = path.name
            rows.append(row)
    return rows, errors


def get_messages(row: dict[str, Any]) -> list[dict[str, Any]]:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return []
    return messages


def message_content(row: dict[str, Any], role: str) -> str:
    for message in get_messages(row):
        if message.get("role") == role:
            content = message.get("content")
            return content if isinstance(content, str) else ""
    return ""


def combined_content(row: dict[str, Any]) -> str:
    return " ".join(
        message.get("content", "")
        for message in get_messages(row)
        if isinstance(message.get("content"), str)
    )


def has_disclaimer(text: str) -> bool:
    return any(marker in text for marker in DISCLAIMER_MARKERS)


def row_label(row: dict[str, Any]) -> str:
    return f"{row.get('_file', '?')}:{row.get('_line', '?')}"


def validate_row(row: dict[str, Any], expected_split: str) -> list[str]:
    errors: list[str] = []
    label = row_label(row)
    messages = get_messages(row)
    if len(messages) != 3:
        errors.append(f"{label}: messages must contain exactly system/user/assistant")
    roles = [message.get("role") for message in messages]
    if roles != ["system", "user", "assistant"]:
        errors.append(f"{label}: messages roles must be system, user, assistant")

    for message in messages:
        role = message.get("role", "<missing>")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"{label}: empty or missing content for role {role}")

    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{label}: metadata must be an object")
        metadata = {}

    for field in ("intent", "topic", "source", "requires_rag", "quality"):
        if field not in metadata:
            errors.append(f"{label}: missing metadata.{field}")
    if metadata.get("quality") != "high":
        errors.append(f"{label}: metadata.quality must be high")
    if metadata.get("split") != expected_split:
        errors.append(f"{label}: metadata.split must be {expected_split}")

    combined = combined_content(row)
    for phrase in UNSAFE_PHRASES:
        if phrase in combined:
            errors.append(f"{label}: unsafe phrase found: {phrase}")

    for phrase in PRETEND_LAWYER_PHRASES:
        if phrase.casefold() in combined.casefold():
            errors.append(f"{label}: assistant must not pretend to be a lawyer")

    for pattern in PII_PATTERNS:
        if pattern.search(combined):
            errors.append(f"{label}: possible private data detected")

    has_article_ref = any(pattern.search(combined) for pattern in FAKE_ARTICLE_PATTERNS)
    if has_article_ref and metadata.get("source") != "insufficient_context":
        errors.append(f"{label}: article/legal-number reference without insufficient_context source")

    assistant = message_content(row, "assistant")
    advice_like = bool(metadata.get("advice_like", metadata.get("requires_rag", True)))
    if advice_like and not has_disclaimer(assistant):
        errors.append(f"{label}: legal-advice-like assistant message needs a disclaimer")

    topic = metadata.get("topic")
    if topic not in REQUIRED_TOPICS:
        errors.append(f"{label}: unknown or missing topic: {topic}")

    return errors


def duplicate_user_inputs(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        user = message_content(row, "user")
        if user.strip():
            counts[normalize_text(user)] += 1
    return {text: count for text, count in counts.items() if count > 1}


def validate_split_integrity(rows_by_split: dict[str, list[dict[str, Any]]]) -> list[str]:
    errors: list[str] = []
    total = sum(len(rows) for rows in rows_by_split.values())
    if total < 1500:
        errors.append(f"combined: expected at least 1500 examples, found {total}")
    for split, expected_count in EXPECTED_SPLIT_COUNTS.items():
        actual = len(rows_by_split.get(split, []))
        if actual != expected_count:
            errors.append(f"{split}: expected {expected_count} examples, found {actual}")

    seen_ids: dict[str, str] = {}
    for split, rows in rows_by_split.items():
        for row in rows:
            example_id = row.get("metadata", {}).get("example_id")
            if not example_id:
                errors.append(f"{row_label(row)}: missing metadata.example_id")
                continue
            if example_id in seen_ids:
                errors.append(f"{row_label(row)}: duplicate example_id also in {seen_ids[example_id]}")
            seen_ids[example_id] = split
    return errors


def validate_topic_distribution(rows: list[dict[str, Any]]) -> tuple[Counter[str], list[str]]:
    counts: Counter[str] = Counter(row.get("metadata", {}).get("topic") for row in rows)
    errors: list[str] = []
    for topic in REQUIRED_TOPICS:
        if counts.get(topic, 0) == 0:
            errors.append(f"combined: missing required topic {topic}")
        elif counts[topic] < 20:
            errors.append(f"combined: weak topic distribution for {topic}: {counts[topic]}")
    return counts, errors


def validate_manifest(total: int) -> list[str]:
    errors: list[str] = []
    if not MANIFEST_PATH.exists():
        return [f"{MANIFEST_PATH}: file does not exist"]
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{MANIFEST_PATH}: invalid JSON: {exc}"]
    if manifest.get("total_examples") != total:
        errors.append(
            f"dataset_manifest.json: total_examples {manifest.get('total_examples')} does not match {total}"
        )
    for split_name, expected in (
        ("train", EXPECTED_SPLIT_COUNTS["train"]),
        ("validation", EXPECTED_SPLIT_COUNTS["val"]),
        ("test", EXPECTED_SPLIT_COUNTS["test"]),
    ):
        actual = manifest.get("splits", {}).get(split_name, {}).get("count")
        if actual != expected:
            errors.append(f"dataset_manifest.json: {split_name} count {actual} != {expected}")
    return errors


def validate_dataset() -> dict[str, Any]:
    rows_by_split: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []

    for split, path in SPLIT_PATHS.items():
        rows, read_errors = read_jsonl(path)
        rows_by_split[split] = rows
        errors.extend(read_errors)
        for row in rows:
            errors.extend(validate_row(row, split))

    all_rows = [row for rows in rows_by_split.values() for row in rows]
    duplicates = duplicate_user_inputs(all_rows)
    for text, count in duplicates.items():
        errors.append(f"duplicate user input appears {count} times: {text}")

    errors.extend(validate_split_integrity(rows_by_split))
    topic_counts, topic_errors = validate_topic_distribution(all_rows)
    errors.extend(topic_errors)
    errors.extend(validate_manifest(len(all_rows)))

    return {
        "ok": not errors,
        "errors": errors,
        "rows_by_split": rows_by_split,
        "total": len(all_rows),
        "duplicates": duplicates,
        "topic_counts": dict(sorted((str(k), v) for k, v in topic_counts.items() if k)),
        "split_counts": {split: len(rows) for split, rows in rows_by_split.items()},
    }


def main() -> None:
    result = validate_dataset()
    print("SFT dataset validation")
    for split, count in result["split_counts"].items():
        print(f"- {split}: {count}")
    print(f"- total: {result['total']}")
    print("- records per topic:")
    for topic, count in result["topic_counts"].items():
        print(f"  - {topic}: {count}")
    print(f"- duplicate user inputs: {len(result['duplicates'])}")

    if result["errors"]:
        print(f"FAIL: {len(result['errors'])} validation error(s)")
        for error in result["errors"][:200]:
            print(f"  - {error}")
        if len(result["errors"]) > 200:
            print(f"  - ... {len(result['errors']) - 200} more")
        raise SystemExit(1)

    print("PASS: dataset is valid")


if __name__ == "__main__":
    main()
