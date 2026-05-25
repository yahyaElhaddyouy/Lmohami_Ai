# Quality Report

## Current Trust Target

- Required pass rate: 90% or better on `backend/eval_cases.jsonl`.
- Current evaluator size: 100+ cases covering common labor-law topics, short Darija, refusals, impossible articles, and hallucination traps.

## Metrics To Track

- Trust score.
- Average latency.
- Timeout count.
- Source count per answer.
- Failed topics.
- Weak retrieval phrases.

## Known Weak Spots

- CNSS details need a direct CNSS source, not only Code du Travail references.
- Accident de travail answers are safer now, but compensation details need stronger dedicated sources.
- Short vague questions still need clarification behavior.

## Next Fixes

1. Add CNSS and accident-work compensation source documents.
2. Add failed real chat logs to `eval_cases.jsonl`.
3. Run 10-minute and 30-minute stress tests.
4. Review answers that fall back to LLM instead of verified rules.
