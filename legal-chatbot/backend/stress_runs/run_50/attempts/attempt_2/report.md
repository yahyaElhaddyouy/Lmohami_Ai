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
- Passed: 47
- Failed: 3
- Pass rate: 94.00%
- Average latency: 7256 ms
- Median latency: 9214 ms
- Max latency: 14681 ms
- Citation accuracy: 31/31 (100.00%)
- Refusal accuracy: 39/42 (92.86%)
- Hallucination rate: 0/50 (0.00%)
- Legal guarantee rate: 0/50 (0.00%)
- Guarantee trap cases: 3

## Presentation Targets

- Stress pass rate >= 90%: PASS
- Hallucination critical cases = 0: PASS
- Legal guarantee cases = 0: PASS
- Citation accuracy >= 95%: PASS
- Refusal accuracy >= 95%: FAIL

## Failures By Type

- conversation_routing_error: 0
- intent_error: 3
- retrieval_error: 0
- citation_error: 0
- refusal_error: 3
- hallucination_error: 0
- legal_guarantee_error: 0
- answer_quality_error: 0
- ux_error: 0
- latency_error: 0
- exception_error: 0

## Failures By Topic

- dismissal: 1/2 (50.0%)
- sick_leave: 1/2 (50.0%)
- vague_dismissal: 1/2 (50.0%)

## Top Weak Topics

- sick_leave: 1/2 failed (50.0%)
- dismissal: 1/2 failed (50.0%)
- vague_dismissal: 1/2 failed (50.0%)

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

- code_travail: 40
- labor_inspection: 9
- work_accident: 5
- cnss: 4

## Failure Examples

- `stress_0012` [sick_leave/arabizi] mrdt o ma 9dertch nmchi lkhdma -> refusal_error, intent_error: expected legal intent in ['sick_leave'], got unclear; concrete labor-law question was refused
- `stress_0022` [vague_dismissal/arabizi] galou lia sir trta7 7ta n3ayto lik -> refusal_error, intent_error: expected legal intent in ['dismissal_unclear', 'dismissal', 'abusive_dismissal'], got unclear; concrete labor-law question was refused
- `stress_0042` [dismissal/arabizi] patron gal lia ma tb9ach tji -> refusal_error, intent_error: expected legal intent in ['dismissal', 'abusive_dismissal', 'dismissal_unclear'], got unclear; concrete labor-law question was refused

## Recommended Fixes


### Critical

- Separate out-of-scope/fake-reference refusal rules from supported labor questions.

### High

- Add focused intent regression cases for the failed Darija/Arabizi formulations.
- Prioritize manual review of the weakest topics: sick_leave, dismissal, vague_dismissal.

### Medium

- No medium-priority weakness was detected in this run.

No fixes were applied by this run. Recommendations require review first.

## Output Files

- `stress_results_2000.jsonl`
- `stress_failures_2000.jsonl`
- `STRESS_EVALUATION_REPORT.md`
