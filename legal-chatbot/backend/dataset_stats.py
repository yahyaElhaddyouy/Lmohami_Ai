"""Show coverage and quality stats for Darija labor-law JSONL datasets."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from generate_paraphrases import INTENT_SEEDS


def read_jsonl(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def duplicate_inputs(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = Counter(" ".join(row.get("input", "").split()).casefold() for row in rows)
    return {text: count for text, count in counts.items() if text and count > 1}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=[
            "data/training/darija_labor_intents_qlora.jsonl",
            "data/evaluation/darija_labor_intents_eval.jsonl",
        ],
    )
    parser.add_argument("--weak-threshold", type=int, default=10)
    args = parser.parse_args()

    rows_by_path: dict[str, list[dict[str, str]]] = {}
    all_rows: list[dict[str, str]] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        rows = read_jsonl(path)
        rows_by_path[str(path)] = rows
        all_rows.extend(rows)

    intent_counts = Counter(row.get("output", "") for row in all_rows if row.get("output"))
    duplicates = duplicate_inputs(all_rows)
    weak_intents = {
        intent: intent_counts.get(intent, 0)
        for intent in sorted(INTENT_SEEDS)
        if intent_counts.get(intent, 0) < args.weak_threshold
    }

    per_file = defaultdict(dict)
    for path, rows in rows_by_path.items():
        counts = Counter(row.get("output", "") for row in rows if row.get("output"))
        per_file[path] = dict(sorted(counts.items()))

    print("Dataset stats")
    print(f"- number of intents: {len(intent_counts)} / {len(INTENT_SEEDS)}")
    print(f"- paraphrase count: {len(all_rows)}")
    print(f"- duplicate inputs: {len(duplicates)}")
    print(f"- weak intents threshold: {args.weak_threshold}")
    if weak_intents:
        print("- weak intents:")
        for intent, count in weak_intents.items():
            print(f"  - {intent}: {count}")
    else:
        print("- weak intents: none")

    print("- records per intent:")
    for intent in sorted(INTENT_SEEDS):
        print(f"  - {intent}: {intent_counts.get(intent, 0)}")

    print("- records per file:")
    for path, counts in per_file.items():
        print(f"  - {path}: {sum(counts.values())}")


if __name__ == "__main__":
    main()
