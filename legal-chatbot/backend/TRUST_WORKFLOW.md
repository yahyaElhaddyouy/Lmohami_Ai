# Trust workflow

This project uses RAG over `data/code_travail_maroc.pdf`. The local Ollama model is not really being trained here; trust comes from better sources, better retrieval, stricter prompting, and repeated evaluation.

## Run the chatbot

```powershell
python rag.py
```

## Run the trust evaluation

Start Ollama first:

```powershell
ollama serve
```

Then run:

```powershell
python evaluate_trust.py --report trust_report.json
```

The evaluator prints a trust score. Treat the chatbot as **not trusted** until it scores at least 90% on a growing set of real questions.

## Keep improving it

1. Ask the bot real legal-work questions.
2. When the answer is wrong, unsafe, missing a citation, or too confident, add that question to `eval_cases.jsonl`.
3. Improve retrieval, chunking, prompt rules, or source documents.
4. Re-run `python evaluate_trust.py --report trust_report.json`.
5. Repeat until the score stays high on old and new cases.

## Eval case format

Each line in `eval_cases.jsonl` is one JSON object:

```json
{"id":"short_name","question":"...","required_terms":["..."],"forbidden_terms":["..."],"expect_refusal":false,"min_sources":1}
```

- `required_terms`: words that should appear in a good answer.
- `forbidden_terms`: unsafe or wrong phrases that must not appear.
- `expect_refusal`: use `true` when the bot should say the source is insufficient or the topic is outside Moroccan labor law.
- `min_sources`: minimum number of legal citations expected in the answer.
