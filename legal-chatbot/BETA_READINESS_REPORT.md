# Lmo7ami AI Beta Readiness Report

## Status

**READY_FOR_BETA** for a monitored private beta.

No training was started. The work was limited to simulation, QA, safe backend fixes, and reporting.

## Final Scores

- Real-user simulation: 300/300 passed, 100.0%
- Trust evaluation: 103/105 passed, 98.1%
- Darija intent evaluation: 100/100 passed, 100%
- Darija priority unit test: PASS
- API readiness checks: PASS

## Real-User Simulation

- Total simulated questions: 300
- Failed: 0
- Average latency: 9463 ms
- Median latency: 10866 ms
- Max latency: 17963 ms
- Failure types: none
- No latency, citation, unsafe guarantee, refusal, UX, or answer-quality failures remained.

## Remaining Failed Examples

- None.

## Fixes Applied

- Added `backend/simulate_real_users.py` and generated simulation JSONL/report artifacts.
- Expanded Darija legal understanding for dismissal, vague dismissal, CNSS, accidents, sick leave, overtime, maternity, preavis, no-contract, CDD/CDI, resignation, and labor inspection.
- Fixed Arabic punctuation word-boundary matching so terms before `؟` and similar punctuation are detected correctly.
- Reduced noisy detector expansion in RAG so verified answers follow the legal analyzer/original question instead of unrelated fuzzy matches.
- Added deterministic source-backed answers for high-frequency beta topics to avoid slow or drifting LLM responses.
- Strengthened out-of-scope, fake article, and legal guarantee refusal behavior.
- Added generic clarification handling for vague rights questions without pretending to know missing facts.
- Added safe clarification for `HR قال سير حتى نعيطو ليك`: "واش بغيتي شهادة العمل ولا كيهضرو معاك على الرجوع للخدمة؟"
- Preserved both `labor_inspection` and `code_travail` sources for mixed inspection + wage questions.

## Source Coverage

- `code_travail`: 195 returned sources
- `labor_inspection`: 72 returned sources
- `cnss`: 21 returned sources
- `work_accident`: 19 returned sources

## Residual Risks

- Mixed-intent questions can still require careful monitoring, especially when users ask about a document and possible return-to-work in the same short phrase.
- Trust evaluation remains trusted at 103/105; the current two misses are citation coverage edge cases, not unsafe answers.
- The simulator is synthetic; the next risk reduction should come from real anonymized beta conversations.

## Recommended Next Step

Start a small monitored private beta, log anonymized failures, and add those cases to the simulator before any QLoRA training.
