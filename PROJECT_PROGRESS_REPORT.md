# Lmo7ami AI Project Progress Report

**Report date:** 2026-05-16  
**Project type:** Moroccan labor law AI chatbot  
**Current overall phase:** Working prototype / early validation  
**Repository status:** Clean on `main` at report time  

## 1. Executive Summary

Lmo7ami AI already has a functioning end-to-end prototype:

- A Python/FastAPI backend exposes a `/chat` API.
- A retrieval-augmented generation pipeline answers questions from the Moroccan labor law PDF.
- A Flutter mobile app provides a polished Arabic-first chat interface.
- A trust-evaluation workflow exists and currently passes its small test set.

The project is beyond the idea stage and already demonstrates its core value. The main work ahead is not "make it exist," but "make it dependable, measurable, and ready for broader use."

## 2. Current Progress Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Product concept | Complete | Clear focus: Moroccan labor law assistant |
| Backend API | Complete for prototype | FastAPI `/` and `/chat` endpoints implemented |
| RAG ingestion | Complete for prototype | PDF ingestion into ChromaDB implemented |
| Retrieval + answer generation | In progress | Semantic search, keyword boosting, topic guards, and one verified rule path exist |
| Mobile UI | Complete for prototype | Splash, chat flow, loading, retry, citations, and disclaimer implemented |
| Trust evaluation | In progress | Automated evaluation exists, but only 4 formal cases |
| Stress testing | In progress | Stress script exists with a larger question bank |
| Automated tests | Minimal | One Flutter widget test; no backend unit/integration test suite visible |
| Deployment readiness | Not started | Current setup is local-machine oriented |
| Production observability | Not started | No logging dashboard, analytics, crash reporting, or monitoring visible |

## 3. What Is Already Built

### Backend

- FastAPI service with `/chat` endpoint returning:
  - `answer`
  - `sources`
- PDF ingestion flow using:
  - `pypdf`
  - `chromadb`
  - Ollama embeddings
- RAG pipeline with:
  - embedding retrieval
  - keyword-based ranking support
  - out-of-scope detection
  - legal-topic expansion
  - citation attachment
  - deterministic verified answer path for annual paid leave
- Local CLI mode for chatbot testing.

### Mobile App

- Flutter application with:
  - splash screen
  - Arabic RTL layout
  - welcome state
  - user/assistant message bubbles
  - loading state
  - retry flow after errors
  - source chips
  - legal disclaimer
  - configurable backend URL
- Android and iOS project scaffolding present.

### Quality / Trust Tooling

- `evaluate_trust.py` with formal pass/fail evaluation.
- `eval_cases.jsonl` test-case format.
- `TRUST_WORKFLOW.md` explaining how to grow trust.
- `stress_questions.py` for repeated question runs.
- Latest stored trust result:
  - **4 / 4 passed**
  - **100% score on current evaluation set**

## 4. Progress by Workstream

### A. Product and UX

| Item | Status | Evidence |
| --- | --- | --- |
| Chat-first experience | Done | Mobile chat screen implemented |
| Arabic RTL support | Done | App locale and directionality configured |
| Friendly error states | Done | Retryable API errors shown in UI |
| Citation display | Done | Source chips shown under assistant responses |
| Legal disclaimer | Done | Persistent disclaimer card present |
| Conversation history persistence | Not started | No local storage or account model visible |
| User onboarding/help | Not started | No onboarding flow or FAQ visible |

### B. Legal Intelligence / RAG

| Item | Status | Evidence |
| --- | --- | --- |
| Source document ingestion | Done | Moroccan labor law PDF ingested |
| Semantic retrieval | Done | Ollama embeddings + ChromaDB |
| Keyword enrichment | Done | Legal term expansion and reranking |
| Out-of-scope refusal | Done for known cases | Explicit refusal path exists |
| Citation enforcement | Partial | Fallback citation appending exists |
| Verified deterministic answers | Partial | Present for paid leave only |
| Broad legal coverage confidence | Not yet proven | Evaluation set still small |
| Multi-document support | Not started | Current system appears tied to one PDF |

### C. Engineering and Reliability

| Item | Status | Evidence |
| --- | --- | --- |
| API contract | Done | Mobile and backend aligned on `answer` + `sources` |
| Timeout handling | Done | Mobile and backend timeouts defined |
| Device networking guidance | Done | README + API config comments |
| Backend automated tests | Not started | No backend test files visible |
| Mobile automated tests | Minimal | One splash-screen widget test |
| Config management | Partial | Environment variables used in backend; hard-coded local URLs remain in mobile |
| Error observability | Minimal | Console/debug logging only |
| CI/CD | Not started | No workflow files visible |

## 5. Current Metrics

| Metric | Current value |
| --- | --- |
| Formal trust cases | 4 |
| Latest formal trust score | 100% |
| Stress-question bank | 64 questions |
| Backend top-level files | 10 |
| Mobile Dart source files | 11 |
| Visible mobile automated tests | 1 |
| Visible backend automated tests | 0 |

**Important note:** the current 100% trust score is encouraging, but it is not yet a strong confidence signal because the formal evaluation set is still very small.

## 6. Key Risks and Gaps

1. **Evaluation coverage is too small**
   - Four formal trust cases are not enough for a legal assistant.
   - The project needs broader cases across termination, wages, leave, contracts, disciplinary procedure, maternity, overtime, refusals, and ambiguous questions.

2. **Prototype behavior is still local-first**
   - The app points to local addresses and relies on local Ollama.
   - There is no visible deployment configuration, authentication, or hosted inference plan.

3. **Limited automated testing**
   - A legal chatbot needs regression protection around retrieval, refusals, citations, and API shape.
   - Current automated test coverage is very light.

4. **One-source dependency**
   - The knowledge base appears centered on a single PDF.
   - That is simple, but fragile if the source is incomplete, outdated, or OCR quality varies.

5. **Operational visibility is weak**
   - There is no visible monitoring for latency, failures, source hit rates, refusal rates, or unsafe answers.

6. **Text encoding/rendering should be checked carefully**
   - Arabic text appears as mojibake in terminal output, which may be a terminal-display issue, but it should be verified end-to-end on target devices and stored reports.

## 7. Recommended Next Milestones

### Milestone 1: Improve Trust Baseline

- Grow `eval_cases.jsonl` from 4 cases to at least 30 meaningful cases.
- Cover:
  - valid labor-law questions
  - out-of-scope questions
  - impossible article references
  - ambiguous questions
  - adversarial prompts
- Add expected outcomes for:
  - refusal behavior
  - minimum citations
  - prohibited unsafe claims

### Milestone 2: Add Test Coverage

- Add backend tests for:
  - out-of-scope detection
  - citation enforcement
  - deterministic verified answers
  - API response shape
- Add mobile tests for:
  - chat submission
  - loading state
  - retry state
  - source rendering

### Milestone 3: Prepare for Real Users

- Move environment-specific URLs out of source-code constants.
- Decide on deployment model for:
  - API host
  - model host
  - vector database
- Add:
  - request logging
  - latency metrics
  - error tracking
  - basic usage analytics

### Milestone 4: Expand Product Depth

- Add conversation persistence.
- Add document/version metadata for legal sources.
- Support more verified rule paths beyond annual paid leave.
- Consider admin tooling for reviewing failures and adding new evaluation cases.

## 8. Suggested Status Labels

Use these labels when tracking tasks:

- **Done**: implemented and verified
- **In progress**: implemented partly or still changing
- **Blocked**: cannot move without another dependency
- **Not started**: no implementation yet
- **Needs validation**: exists, but confidence is not yet high enough

## 9. Weekly Tracking Template

Use this section every week.

### Week of: `YYYY-MM-DD`

| Category | Last week | This week | Status |
| --- | --- | --- | --- |
| Backend |  |  |  |
| Mobile |  |  |  |
| RAG quality |  |  |  |
| Testing |  |  |  |
| Deployment |  |  |  |
| Documentation |  |  |  |

### Weekly metrics

| Metric | Previous | Current | Trend |
| --- | --- | --- | --- |
| Formal eval cases |  |  |  |
| Formal trust score |  |  |  |
| Stress pass rate |  |  |  |
| Open bugs |  |  |  |
| Automated tests |  |  |  |
| Average response time |  |  |  |

### This week's accomplishments

- 

### Current blockers

- 

### Next week's priorities

1. 
2. 
3. 

## 10. Definition of "Ready for Wider Testing"

The project is ready for broader external testing when:

- Formal trust set reaches at least 30-50 cases.
- Trust score remains above 90% across repeated runs.
- Out-of-scope and hallucination guardrails are validated.
- Backend has basic automated tests.
- Mobile app has tests for key chat states.
- Deployment no longer depends on developer-local networking.
- Source freshness and document provenance are documented.

## 11. Current Overall Assessment

**Current maturity:** early but real product prototype  
**Best strength:** complete end-to-end user journey already exists  
**Main weakness:** quality confidence is not yet broad enough for a legal domain  
**Most valuable next move:** expand the evaluation suite before adding many new features
