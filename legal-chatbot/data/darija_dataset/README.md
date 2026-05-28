# Moroccan Darija Legal Understanding Dataset

This folder contains the first-stage understanding layer for Lmo7ami AI. It is
used to detect informal Moroccan Darija labor-law intent, normalize the query
with Arabic/French legal keywords, and decide whether the RAG pipeline should be
called.

Files:

- `intents.json`: intent metadata, keywords, and normalized legal queries.
- `darija_examples.jsonl`: generated Darija examples for intent detection.
- `darija_eval.jsonl`: held-out evaluation questions with expected intents.
- `weak_cases.jsonl`: manually collected failures to review and fold into the generator.

This is not a fine-tuning dataset yet. Keep it source-controlled, review weak
cases, then regenerate with `python darija_dataset_builder.py`.
