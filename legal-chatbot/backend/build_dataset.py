"""Build QLoRA-ready Darija labor-law intent datasets."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from generate_paraphrases import INTENT_SEEDS, iter_records, write_jsonl


DEFAULT_SYNTHETIC = Path("data/synthetic/darija_labor_intents.jsonl")
DEFAULT_TRAINING = Path("data/training/darija_labor_intents_qlora.jsonl")
DEFAULT_EVALUATION = Path("data/evaluation/darija_labor_intents_eval.jsonl")
DEFAULT_MANIFEST = Path("data/training/darija_labor_dataset_manifest.json")


def read_jsonl(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return rows


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (
            " ".join(row.get("instruction", "").split()),
            " ".join(row.get("input", "").split()).casefold(),
            " ".join(row.get("output", "").split()),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def stratified_split(
    rows: list[dict[str, str]], eval_per_intent: int, seed: int
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rng = random.Random(seed)
    by_intent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_intent[row["output"]].append(row)

    training: list[dict[str, str]] = []
    evaluation: list[dict[str, str]] = []
    for intent in sorted(by_intent):
        intent_rows = list(by_intent[intent])
        rng.shuffle(intent_rows)
        split_at = min(eval_per_intent, max(1, len(intent_rows) // 5))
        evaluation.extend(intent_rows[:split_at])
        training.extend(intent_rows[split_at:])

    rng.shuffle(training)
    rng.shuffle(evaluation)
    return training, evaluation


def write_manifest(path: Path, training: list[dict[str, str]], evaluation: list[dict[str, str]]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for row in training + evaluation:
        counts[row["output"]] += 1

    manifest = {
        "format": "jsonl",
        "schema": ["instruction", "input", "output"],
        "task": "Moroccan Darija labor-law intent classification",
        "country_scope": "Morocco",
        "intents": sorted(INTENT_SEEDS),
        "intent_count": len(INTENT_SEEDS),
        "training_records": len(training),
        "evaluation_records": len(evaluation),
        "total_records": len(training) + len(evaluation),
        "records_per_intent": dict(sorted(counts.items())),
        "qlora_note": (
            "Use instruction/input/output as supervised fine-tuning text. "
            "Outputs are canonical intent labels, not legal advice."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", default=str(DEFAULT_SYNTHETIC))
    parser.add_argument("--training", default=str(DEFAULT_TRAINING))
    parser.add_argument("--evaluation", default=str(DEFAULT_EVALUATION))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--eval-per-intent", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    synthetic_path = Path(args.synthetic)
    synthetic_rows = read_jsonl(synthetic_path)
    if not synthetic_rows:
        synthetic_rows = iter_records()
        write_jsonl(synthetic_path, synthetic_rows)

    rows = dedupe_rows(synthetic_rows)
    training, evaluation = stratified_split(rows, args.eval_per_intent, args.seed)

    write_jsonl(Path(args.training), training)
    write_jsonl(Path(args.evaluation), evaluation)
    write_manifest(Path(args.manifest), training, evaluation)

    print(f"Wrote {len(training)} training rows to {args.training}")
    print(f"Wrote {len(evaluation)} evaluation rows to {args.evaluation}")
    print(f"Wrote manifest to {args.manifest}")


if __name__ == "__main__":
    main()
