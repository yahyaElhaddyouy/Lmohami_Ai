# Lmo7ami AI Project State

Generated: 2026-05-25

This document captures the current state before further engineering work. It is intentionally descriptive only: no code changes are included in this milestone.

## Architecture

Lmo7ami AI is a Moroccan labor-law assistant with a FastAPI backend, local Ollama models, ChromaDB retrieval, an offline Darija intent detector, trust evaluation scripts, and a Flutter mobile client.

Current request flow:

1. Flutter sends `POST /chat` with `{ "question": "..." }`.
2. `backend/main.py` validates the request and calls `ask_chatbot()`.
3. `backend/rag.py` handles native conversation routing, Darija intent detection, query expansion, retrieval from ChromaDB, verified rule answers, LLM fallback, citation validation, and refusal behavior.
4. `backend/darija_intent.py` detects conversational and legal intents from local JSON/JSONL resources.
5. ChromaDB stores chunks from the Moroccan labor code PDF.
6. Ollama provides embeddings through `nomic-embed-text` and generation through `qwen2.5:7b`.
7. The API returns `{ answer, sources }`; Flutter parses this through `ChatResponse`.

## Current Files

Top-level documentation and planning:

- `README.md`
- `ROADMAP.md`
- `MODEL_STRATEGY.md`
- `FRONTEND_UX_PLAN.md`
- `DEPLOYMENT.md`
- `quality_report.md`
- `PROJECT_STATE.md`

Backend core:

- `backend/main.py`: FastAPI app, health/model endpoints, `/chat`, API-key middleware, CORS.
- `backend/rag.py`: main RAG and answer orchestration file.
- `backend/darija_intent.py`: offline intent detection and direct conversational answers.
- `backend/ingest.py`: current ingestion for a single labor-code PDF into ChromaDB.
- `backend/requirements.txt`: Python runtime dependencies.

Backend evaluation and data tools:

- `backend/evaluate_trust.py`: trust/evaluation runner over `eval_cases.jsonl`.
- `backend/evaluate_darija_intent.py`: Darija intent evaluation runner.
- `backend/eval_cases.jsonl`: current trust cases, counted at 105 lines.
- `backend/dataset_stats.py`: dataset reporting script.
- `backend/darija_dataset_builder.py`: Darija dataset builder.
- `backend/build_dataset.py`, `backend/generate_paraphrases.py`, `backend/validate_dataset.py`, `backend/stress_questions.py`.

Backend data:

- `backend/data/code_travail_maroc.pdf`: current legal source PDF.
- `backend/chroma_db/`: local ChromaDB store.
- `backend/data/training/`: training and manifest JSONL files.
- `backend/data/synthetic/`: synthetic intent data.
- `backend/data/evaluation/`: evaluation JSONL files.
- `backend/data/real_cases/`: placeholder/README for real cases.

Darija dataset:

- `data/darija_dataset/intents.json`
- `data/darija_dataset/darija_examples.jsonl`: counted at 1000 examples.
- `data/darija_dataset/darija_eval.jsonl`: counted at 100 eval cases.
- `data/darija_dataset/weak_cases.jsonl`
- `data/darija_dataset/README.md`

Flutter mobile client:

- `mobile/lib/main.dart`
- `mobile/lib/screens/chat_screen.dart`
- `mobile/lib/screens/splash_screen.dart`
- `mobile/lib/services/chat_api_service.dart`
- `mobile/lib/config/api_config.dart`
- `mobile/lib/models/chat_message.dart`
- `mobile/lib/models/chat_response.dart`
- `mobile/lib/widgets/message_bubble.dart`
- `mobile/lib/widgets/source_chip.dart`
- `mobile/lib/widgets/chat_input_bar.dart`
- `mobile/lib/theme/app_theme.dart`
- Android and iOS platform folders are present.

## Dependencies

Backend Python dependencies from `backend/requirements.txt`:

- `chromadb`
- `pypdf`
- `requests`
- `arabic-reshaper`
- `python-bidi`
- `fastapi`
- `uvicorn`

Backend external services:

- Ollama chat endpoint: default `http://localhost:11434/api/chat`
- Ollama embedding endpoint: default `http://localhost:11434/api/embeddings`
- Chat model: default `qwen2.5:7b`
- Embedding model: default `nomic-embed-text`

Flutter dependencies from `mobile/pubspec.yaml`:

- Flutter SDK
- `flutter_localizations`
- `http`
- `cupertino_icons`
- `flutter_lints` for dev linting

## Current Validation Baseline

Known recent validation in this workspace:

- `backend/evaluate_darija_intent.py`: 100/100 PASS.
- `backend/evaluate_trust.py`: recently observed at 105/105 PASS after latest stabilization changes.
- The operational safety gate should remain: trust evaluation must stay at or above 92%.

Before any future code change, rerun at least:

```powershell
python -m py_compile backend/rag.py backend/darija_intent.py backend/main.py
python backend/evaluate_darija_intent.py
python backend/evaluate_trust.py
```

For Flutter changes, also run from `mobile/`:

```powershell
flutter analyze
flutter test
```

## Risk Areas

High-risk backend areas:

- `backend/rag.py` is large and contains many responsibilities: retrieval, intent expansion, conversation routing, verified answers, prompt construction, validation, citation policy, and CLI behavior.
- Retrieval quality depends on hand-built topic maps, keyword scoring, anchors, ChromaDB vectors, and local PDF chunk quality.
- Citation handling is safety-critical: citations should appear only for retrieved legal answers, not native chat or refusals.
- Refusal behavior is safety-critical: the assistant must refuse when context is missing or irrelevant.
- Article-number validation must prevent invented legal articles.
- Intent expansion can improve retrieval but can also bias answers if downstream logic treats expansion terms as user-provided facts.
- Verified answers are currently embedded inside `rag.py`; this makes changes harder to isolate.
- `ingest.py` deletes and recreates the collection, so it is not yet safe for incremental multi-source ingestion.

High-risk data areas:

- Darija examples currently total 1000, below the requested 3000 target.
- Weak cases and ambiguity handling need systematic expansion.
- Synthetic examples can create repeated patterns and overfit the detector if not deduplicated.
- Mixed Arabic/French/Darija spelling variations are only partially covered.

High-risk mobile areas:

- `ApiConfig.environment` currently selects `ngrokPublic` by default.
- Real-phone LAN, emulator, and ngrok require different URLs.
- Error text and mojibake risk should be checked carefully in Flutter files.
- UX should improve incrementally without redesigning the whole app.

High-risk production areas:

- No Docker/runtime supervision is confirmed yet.
- No durable observability pipeline is present.
- No structured metrics store is present.
- API key support exists, but production secret management is not documented as complete.
- HTTPS/Nginx/VPS deployment needs verification.

## Missing Features

Stabilization and tests:

- Add regression tests around native conversation replies, citation policy, refusals, and high-risk legal intents.
- Add tests for API response compatibility: `answer` string plus `sources` list.
- Add tests that prevent generic clarification questions from leaking into unrelated intents.

Darija understanding:

- Grow `data/darija_dataset/` from 1000 examples to 3000 examples.
- Deduplicate examples and normalize variants.
- Add slang, short questions, misspellings, mixed French/Arabic, and ambiguity cases.
- Keep `dataset_stats.py` as the reporting source for dataset coverage and duplicates.

Retrieval:

- Add `retrieve_confidence()` using vector distance, keyword overlap, topic anchors, and source count.
- Use low retrieval confidence to ask clarification instead of hallucinating.
- Keep query expansion separated from user facts.

Human conversation:

- Keep native replies concise and natural.
- Avoid fake empathy and repeated wording.
- Keep clarification questions intent-specific.

Legal knowledge expansion:

- Add source folders:
  - `data/code_travail/`
  - `data/constitution/`
  - `data/cnss/`
  - `data/labor_inspection/`
- Update ingestion to support metadata:
  - source type
  - source name
  - page
  - article when available
  - language
  - ingestion timestamp/version
- Support incremental ingestion instead of full collection deletion.

Verified answers:

- Extract deterministic source-grounded answers from `rag.py` into `backend/verified_rules.py`.
- Cover dismissal, salary, CNSS, accident, leave, contract, and maternity.

Flutter UX:

- Loading state polish.
- Source cards.
- Retry action.
- Clear chat.
- Better error display.
- RTL polish.
- Dark mode.
- Avoid broad redesign.

Observability:

- Create `logs/` and `metrics/`.
- Track latency, retrieval confidence, selected pages, answer type, refusals, and errors.

Evaluation:

- Expand `backend/eval_cases.jsonl` to 500 cases.
- Track source quality, refusal quality, hallucinations, and native conversation behavior.
- Regenerate `quality_report.md` after each evaluation milestone.

Production readiness:

- Complete Docker instructions.
- Complete VPS deployment guide.
- Add Nginx reverse proxy config.
- Add HTTPS/Certbot guidance.
- Add model/chroma persistence notes.

## Next Recommended Milestone

Milestone 1 should be stabilization only:

1. Add a small regression test file for current behavior.
2. Cover native replies with no sources.
3. Cover legal answers with required citations.
4. Cover out-of-scope refusals with no sources.
5. Cover intent-specific clarification behavior.
6. Run compile, Darija intent evaluation, trust evaluation, and Flutter checks if mobile files change.

No new features should be started until this regression harness exists and passes.
