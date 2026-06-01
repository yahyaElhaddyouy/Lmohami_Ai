# Lmo7ami SFT Dataset

This folder contains a supervised fine-tuning dataset for Moroccan Darija legal-assistant behavior.

The examples are designed to teach:

- Moroccan Darija understanding, including slang, typos, and French/Darija mixing.
- A cautious Moroccan labor-law assistant tone.
- Practical next steps and evidence-gathering guidance.
- Refusal behavior for out-of-scope, fake citation, and legal-guarantee requests.
- Clarification behavior when the user question is underspecified.

The examples are **not** intended to teach the model to memorize Moroccan law. Legal facts, exact rules, and article-level references must still come from the RAG pipeline.

## Files

- `lmo7ami_sft_train.jsonl`: 80% training split.
- `lmo7ami_sft_val.jsonl`: 10% validation split.
- `lmo7ami_sft_test.jsonl`: 10% test split.
- `dataset_manifest.json`: dataset metadata, split counts, coverage, and guardrails.
- `README.md`: this note.

## Format

Each JSONL row is a chat-style record:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "intent": "dismissal_unclear",
    "topic": "dismissal",
    "source": "synthetic_curated",
    "requires_rag": true,
    "quality": "high"
  }
}
```

## Rebuild And Validate

Run from `backend/`:

```powershell
python build_sft_dataset.py
python validate_sft_dataset.py
python dataset_stats.py
```

Do not start QLoRA training until the validation script passes and the report has been reviewed.
