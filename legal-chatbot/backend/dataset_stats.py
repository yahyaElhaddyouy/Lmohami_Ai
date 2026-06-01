"""Print SFT dataset stats and write training_dataset_report.md."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from validate_sft_dataset import DATA_DIR, MANIFEST_PATH, duplicate_user_inputs, validate_dataset


REPORT_PATH = Path(__file__).resolve().parents[1] / "training_dataset_report.md"


def message_content(row: dict[str, Any], role: str) -> str:
    for message in row.get("messages", []):
        if message.get("role") == role:
            content = message.get("content")
            return content if isinstance(content, str) else ""
    return ""


def flatten_rows(rows_by_split: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split_rows in rows_by_split.values():
        rows.extend(split_rows)
    return rows


def count_by_metadata(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(row.get("metadata", {}).get(key, "")) for row in rows)
    counts.pop("", None)
    return dict(sorted(counts.items()))


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def build_report(result: dict[str, Any]) -> str:
    rows = flatten_rows(result["rows_by_split"])
    duplicates = duplicate_user_inputs(rows)
    topic_counts = count_by_metadata(rows, "topic")
    intent_counts = count_by_metadata(rows, "intent")
    requires_rag_count = sum(1 for row in rows if row.get("metadata", {}).get("requires_rag") is True)
    manifest = load_manifest()
    errors = result["errors"]

    lines = [
        "# Lmo7ami SFT Training Dataset Report",
        "",
        "## Summary",
        "",
        f"- Total examples: {len(rows)}",
        f"- Train examples: {len(result['rows_by_split'].get('train', []))}",
        f"- Validation examples: {len(result['rows_by_split'].get('val', []))}",
        f"- Test examples: {len(result['rows_by_split'].get('test', []))}",
        f"- Requires RAG examples: {requires_rag_count}",
        f"- Duplicate user input count: {len(duplicates)}",
        f"- Validation errors: {len(errors)}",
        "",
        "## Examples Per Topic",
        "",
    ]

    for topic, count in topic_counts.items():
        lines.append(f"- {topic}: {count}")

    lines.extend(["", "## Examples Per Intent", ""])
    for intent, count in intent_counts.items():
        lines.append(f"- {intent}: {count}")

    lines.extend(["", "## Validation Errors", ""])
    if errors:
        for error in errors:
            lines.append(f"- {error}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Dataset Files",
            "",
            f"- Training directory: `{DATA_DIR.relative_to(Path(__file__).resolve().parents[1])}`",
            "- Train split: `data/training/lmo7ami_sft_train.jsonl`",
            "- Validation split: `data/training/lmo7ami_sft_val.jsonl`",
            "- Test split: `data/training/lmo7ami_sft_test.jsonl`",
            "- Manifest: `data/training/dataset_manifest.json`",
            "",
            "## Recommended Next Step",
            "",
        ]
    )

    if errors:
        lines.append("Fix the dataset and rerun `python validate_sft_dataset.py` before any QLoRA training.")
    else:
        lines.append(
            "Review a small random sample from each split manually, then wire these files into the QLoRA training job without bypassing RAG for legal facts."
        )

    if manifest:
        lines.extend(
            [
                "",
                "## Manifest Snapshot",
                "",
                f"- Dataset version: {manifest.get('version', 'unknown')}",
                f"- Generator: `{manifest.get('generator', 'unknown')}`",
                f"- Format: {manifest.get('format', 'unknown')}",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    result = validate_dataset()
    report = build_report(result)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("SFT dataset stats")
    print(f"- total examples: {result['total']}")
    print("- split counts:")
    for split, count in result["split_counts"].items():
        print(f"  - {split}: {count}")
    print("- examples per topic:")
    for topic, count in result["topic_counts"].items():
        print(f"  - {topic}: {count}")
    print(f"- duplicate count: {len(result['duplicates'])}")
    print(f"- validation errors: {len(result['errors'])}")
    print(f"- report: {REPORT_PATH.relative_to(Path(__file__).resolve().parents[1])}")


if __name__ == "__main__":
    main()
