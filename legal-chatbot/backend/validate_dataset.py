"""Validate Darija labor-law JSONL datasets for SFT safety and consistency."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from generate_paraphrases import INTENT_SEEDS


REQUIRED_FIELDS = ("instruction", "input", "output")
VALID_INTENTS = set(INTENT_SEEDS)

UNSAFE_GUARANTEES = [
    "نضمن",
    "مضمون تربح",
    "أكيد تربح",
    "ربح مؤكد",
    "guaranteed",
    "100%",
]
NON_MOROCCAN_LAW = [
    "code du travail francais",
    "droit francais",
    "france",
    "tunisie",
    "algerie",
    "canada",
    "us law",
]
FAKE_LAW_PATTERNS = [
    re.compile(r"\barticle\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bart\.?\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bloi\s+n[°o]?\s*\d", re.IGNORECASE),
    re.compile(r"المادة\s+\d+"),
    re.compile(r"القانون\s+رقم\s+\d+"),
]


def read_jsonl(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            row["_line"] = line_number
            rows.append(row)
    return rows


def contains_any(text: str, needles: list[str]) -> list[str]:
    lowered = text.casefold()
    return [needle for needle in needles if needle.casefold() in lowered]


def validate_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    input_counter: Counter[str] = Counter()
    for row in rows:
        line = row.get("_line", "?")
        for field in REQUIRED_FIELDS:
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"line {line}: missing or empty field '{field}'")

        output = row.get("output", "")
        if output and output not in VALID_INTENTS:
            errors.append(f"line {line}: unknown intent '{output}'")
        input_text = " ".join(str(row.get("input", "")).split()).casefold()
        if input_text:
            input_counter[input_text] += 1

        combined = " ".join(str(row.get(field, "")) for field in REQUIRED_FIELDS)
        for phrase in contains_any(combined, UNSAFE_GUARANTEES):
            errors.append(f"line {line}: unsafe legal guarantee phrase '{phrase}'")
        for phrase in contains_any(combined, NON_MOROCCAN_LAW):
            errors.append(f"line {line}: non-Moroccan law reference '{phrase}'")
        for pattern in FAKE_LAW_PATTERNS:
            if pattern.search(combined):
                errors.append(
                    f"line {line}: specific law/article citation is not allowed without verified source"
                )

    for text, count in input_counter.items():
        if count > 1:
            errors.append(f"duplicate input appears {count} times: '{text}'")

    return errors


def validate_coverage(rows: list[dict[str, str]], min_per_intent: int) -> list[str]:
    errors: list[str] = []
    intent_counter = Counter(row.get("output", "") for row in rows)
    for intent in sorted(VALID_INTENTS):
        count = intent_counter[intent]
        if count < min_per_intent:
            errors.append(f"weak intent '{intent}': only {count} rows, minimum is {min_per_intent}")
    return errors


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
    parser.add_argument("--min-per-intent", type=int, default=7)
    args = parser.parse_args()

    had_errors = False
    all_rows: list[dict[str, str]] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.exists():
            print(f"FAIL {path}: file does not exist")
            had_errors = True
            continue
        rows = read_jsonl(path)
        all_rows.extend(rows)
        errors = validate_rows(rows)
        if errors:
            had_errors = True
            print(f"FAIL {path}: {len(errors)} issue(s)")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path}: {len(rows)} rows")

    coverage_errors = validate_coverage(all_rows, args.min_per_intent)
    if coverage_errors:
        had_errors = True
        print(f"FAIL combined coverage: {len(coverage_errors)} issue(s)")
        for error in coverage_errors:
            print(f"  - {error}")
    elif all_rows:
        print(f"PASS combined coverage: {len(all_rows)} rows across {len(VALID_INTENTS)} intents")

    raise SystemExit(1 if had_errors else 0)


if __name__ == "__main__":
    main()
