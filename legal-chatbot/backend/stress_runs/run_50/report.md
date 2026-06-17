# Lmo7ami AI Stress Evaluation Report

## Run Status

- Status: **COMPLETE**
- Requested questions: 50
- Completed questions: 50
- Deterministic seed: 20260609
- Latency failure threshold: 30000 ms
- Production code changed by this evaluator: no
- Model training performed: no

## Summary

- Total questions: 50
- Passed: 50
- Failed: 0
- Pass rate: 100.00%
- Average latency: 6300 ms
- Median latency: 7636 ms
- Max latency: 12462 ms
- Citation accuracy: 34/34 (100.00%)
- Refusal accuracy: 42/42 (100.00%)
- Hallucination rate: 0/50 (0.00%)
- Legal guarantee rate: 0/50 (0.00%)
- Guarantee trap cases: 3

## Presentation Targets

- Stress pass rate >= 90%: PASS
- Hallucination critical cases = 0: PASS
- Legal guarantee cases = 0: PASS
- Citation accuracy >= 95%: PASS
- Refusal accuracy >= 95%: PASS

## Failures By Type

- conversation_routing_error: 0
- intent_error: 0
- retrieval_error: 0
- citation_error: 0
- refusal_error: 0
- hallucination_error: 0
- legal_guarantee_error: 0
- answer_quality_error: 0
- ux_error: 0
- latency_error: 0
- exception_error: 0

## Failures By Topic

- None

## Top Weak Topics

- None detected

## Question Style Distribution

- darija_arabic: 5
- arabizi: 5
- mixed_french_darija: 5
- typos: 5
- vague: 5
- angry: 5
- polite: 5
- incomplete_facts: 5
- emotional: 5
- legal_trap: 5

## Source Category Distribution

- code_travail: 45
- labor_inspection: 9
- work_accident: 5
- cnss: 4

## Failure Examples

- None

## Recommended Fixes


### Critical

- No critical failure class was detected; keep the current safety gates.

### High

- No high-priority weakness was detected; expand with anonymized beta cases.

### Medium

- No medium-priority weakness was detected in this run.

No fixes were applied by this run. Recommendations require review first.

## Output Files

- `stress_results_2000.jsonl`
- `stress_failures_2000.jsonl`
- `STRESS_EVALUATION_REPORT.md`
