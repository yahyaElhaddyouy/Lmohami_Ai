# Model Strategy

## Phase 1: Prompt And RAG Optimization

This is the current phase.

- Improve Darija legal concept mapping.
- Keep verified deterministic answers for high-risk recurring topics.
- Expand eval cases before changing the model.
- Tune prompts for short, source-grounded Darija answers.
- Track failed queries and add them to `backend/eval_cases.jsonl`.

## Phase 2: Dataset Building

Training data lives in `backend/data/training/`:

- `darija_legal_qa.jsonl`
- `refusals.jsonl`
- `paraphrases.jsonl`
- `eval_real_cases.jsonl`

Each line uses:

```json
{"instruction":"...","input":"...","output":"..."}
```

Target size:

- Minimum: 500 high-quality examples.
- Better: 2,000+ examples.

Prioritize real Moroccan phrasing, short informal questions, refusals, and paraphrases of the same legal intent.

## Phase 3: Adaptation

Do not fine-tune yet. Start LoRA or QLoRA only after the dataset is clean and evaluation is stable.

Recommended models:

- `qwen2.5:7b` for local UX.
- `llama3.1:8b` for stronger reasoning.
- A small classifier model only if intent routing becomes a bottleneck.

Fine-tuning must never replace RAG citations or refusal logic.
