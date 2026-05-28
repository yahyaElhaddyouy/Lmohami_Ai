# -*- coding: utf-8 -*-
"""Evaluate offline Darija intent detection accuracy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from darija_intent import detect_darija_intent


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EVAL_PATH = BASE_DIR.parent / "data" / "darija_dataset" / "darija_eval.jsonl"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}") from exc
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval", default=str(DEFAULT_EVAL_PATH))
    parser.add_argument("--target", type=float, default=0.90)
    args = parser.parse_args()

    cases = load_jsonl(Path(args.eval))
    if not cases:
        print("No evaluation cases found.")
        return 1

    passed = 0
    failures: list[dict[str, object]] = []

    for case in cases:
        question = str(case["question"])
        expected = str(case["expected_intent"])
        result = detect_darija_intent(question)
        ok = result.intent == expected
        passed += int(ok)
        if not ok:
            failures.append(
                {
                    "id": case.get("id"),
                    "question": question,
                    "expected": expected,
                    "actual": result.intent,
                    "confidence": result.confidence,
                    "matched_by": result.matched_by,
                }
            )

    accuracy = passed / len(cases)
    print(f"Accuracy: {passed}/{len(cases)} ({accuracy:.1%})")
    print("Status:", "PASS" if accuracy >= args.target else "FAIL")
    if failures:
        print("Failures:")
        for failure in failures[:25]:
            print(
                f"- {failure['id']}: expected={failure['expected']} "
                f"actual={failure['actual']} confidence={failure['confidence']} "
                f"question={failure['question']}"
            )

    return 0 if accuracy >= args.target else 1


if __name__ == "__main__":
    raise SystemExit(main())
