"""Validate the broad Moroccan Darija comprehension SFT dataset."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from download_external_darija import dedupe_key


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data" / "training"
SPLITS = {
    "train": DATA_DIR / "darija_comprehension_train.jsonl",
    "val": DATA_DIR / "darija_comprehension_val.jsonl",
    "test": DATA_DIR / "darija_comprehension_test.jsonl",
}
EXPECTED_COUNTS = {"train": 8000, "val": 1000, "test": 1000}
MANIFEST_PATH = DATA_DIR / "darija_comprehension_manifest.json"

UNSAFE_PHRASES = ("نضمن ليك", "أكيد تربح", "غادي تربح")
PRETEND_LAWYER = ("أنا محامي", "بصفتي محامي", "كمحامي", "je suis avocat", "i am a lawyer")
BOUNDARY_MARKERS = ("مدونة الشغل", "الشغل", "خارج نطاقي", "خارج النطاق", "ماشي استشارة قانونية")
PII_PATTERNS = (
    re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE),
    re.compile(r"\b(?:\+?212|0)[5-7]\d{8}\b"),
)


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


def label(row: dict[str, Any]) -> str:
    return f"{row.get('_file', '?')}:{row.get('_line', '?')}"


def messages(row: dict[str, Any]) -> list[dict[str, Any]]:
    value = row.get("messages")
    return value if isinstance(value, list) else []


def content(row: dict[str, Any], role: str) -> str:
    for message in messages(row):
        if message.get("role") == role and isinstance(message.get("content"), str):
            return message["content"]
    return ""


def validate_row(row: dict[str, Any], split: str) -> list[str]:
    errors: list[str] = []
    row_label = label(row)
    row_messages = messages(row)
    if [message.get("role") for message in row_messages] != ["system", "user", "assistant"]:
        errors.append(f"{row_label}: messages must be system/user/assistant")
    for message in row_messages:
        if not isinstance(message.get("content"), str) or not message["content"].strip():
            errors.append(f"{row_label}: empty message content")

    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{row_label}: metadata must be an object")
        metadata = {}

    required = ("intent", "topic", "mode", "source", "raw_ref", "requires_rag", "legal_dataset", "quality", "split")
    for field in required:
        if field not in metadata:
            errors.append(f"{row_label}: missing metadata.{field}")
    if metadata.get("split") != split:
        errors.append(f"{row_label}: metadata.split must be {split}")
    if metadata.get("intent") != "broad_darija_comprehension":
        errors.append(f"{row_label}: wrong intent")
    if metadata.get("legal_dataset") is not False:
        errors.append(f"{row_label}: metadata.legal_dataset must be false")
    if metadata.get("requires_rag") is not False:
        errors.append(f"{row_label}: requires_rag must be false")

    assistant = content(row, "assistant")
    combined = " ".join(content(row, role) for role in ("system", "user", "assistant"))
    for phrase in UNSAFE_PHRASES:
        if phrase in combined:
            errors.append(f"{row_label}: unsafe guarantee phrase: {phrase}")
    for phrase in PRETEND_LAWYER:
        if phrase.casefold() in assistant.casefold():
            errors.append(f"{row_label}: assistant pretends to be a lawyer")
    if not any(marker in assistant for marker in BOUNDARY_MARKERS):
        errors.append(f"{row_label}: assistant should keep legal/off-topic boundary")
    for pattern in PII_PATTERNS:
        if pattern.search(combined):
            errors.append(f"{row_label}: possible private data detected")
    return errors


def validate() -> dict[str, Any]:
    errors: list[str] = []
    rows_by_split: dict[str, list[dict[str, Any]]] = {}
    for split, path in SPLITS.items():
        rows, read_errors = read_jsonl(path)
        rows_by_split[split] = rows
        errors.extend(read_errors)
        if len(rows) != EXPECTED_COUNTS[split]:
            errors.append(f"{split}: expected {EXPECTED_COUNTS[split]} rows, found {len(rows)}")
        for row in rows:
            errors.extend(validate_row(row, split))

    all_rows = [row for rows in rows_by_split.values() for row in rows]
    user_counts = Counter(dedupe_key(content(row, "user")) for row in all_rows)
    duplicates = {text: count for text, count in user_counts.items() if text and count > 1}
    for text, count in duplicates.items():
        errors.append(f"duplicate user text appears {count} times: {text[:120]}")

    ids = Counter(str(row.get("metadata", {}).get("example_id", "")) for row in all_rows)
    duplicate_ids = [example_id for example_id, count in ids.items() if example_id and count > 1]
    for example_id in duplicate_ids:
        errors.append(f"duplicate example_id: {example_id}")

    mode_counts = Counter(str(row.get("metadata", {}).get("mode", "")) for row in all_rows)
    if not MANIFEST_PATH.exists():
        errors.append(f"{MANIFEST_PATH}: manifest missing")
    else:
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            if manifest.get("total_examples") != len(all_rows):
                errors.append("manifest total_examples does not match dataset")
        except json.JSONDecodeError as exc:
            errors.append(f"{MANIFEST_PATH}: invalid JSON: {exc}")

    return {
        "ok": not errors,
        "errors": errors,
        "split_counts": {split: len(rows) for split, rows in rows_by_split.items()},
        "total": len(all_rows),
        "duplicates": duplicates,
        "mode_counts": dict(sorted(mode_counts.items())),
    }


def main() -> int:
    result = validate()
    print("Darija comprehension SFT validation")
    for split, count in result["split_counts"].items():
        print(f"- {split}: {count}")
    print(f"- total: {result['total']}")
    print(f"- duplicate user texts: {len(result['duplicates'])}")
    print("- examples per mode:")
    for mode, count in result["mode_counts"].items():
        print(f"  - {mode}: {count}")

    if result["errors"]:
        print(f"FAIL: {len(result['errors'])} validation error(s)")
        for error in result["errors"][:200]:
            print(f"  - {error}")
        if len(result["errors"]) > 200:
            print(f"  - ... {len(result['errors']) - 200} more")
        return 1

    print("PASS: Darija comprehension SFT dataset is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
