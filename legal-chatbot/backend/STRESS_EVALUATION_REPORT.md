# Lmo7ami AI Stress Evaluation Report

## Run Status

- Status: **IN PROGRESS**
- Requested questions: 2000
- Completed questions: 25
- Deterministic seed: 20260609
- Latency failure threshold: 30000 ms
- Production code changed by this evaluator: no
- Model training performed: no

## Summary

- Total questions: 25
- Passed: 9
- Failed: 16
- Pass rate: 36.00%
- Average latency: 38456 ms
- Median latency: 46908 ms
- Max latency: 95168 ms
- Citation accuracy: 12/15 (80.00%)
- Refusal accuracy: 19/20 (95.00%)
- Hallucination rate: 0/25 (0.00%)
- Legal guarantee rate: 0/25 (0.00%)
- Guarantee trap cases: 1

## Presentation Targets

- Stress pass rate >= 90%: FAIL
- Hallucination critical cases = 0: PASS
- Legal guarantee cases = 0: PASS
- Citation accuracy >= 95%: FAIL
- Refusal accuracy >= 95%: PASS

## Failures By Type

- conversation_routing_error: 1
- intent_error: 0
- retrieval_error: 0
- citation_error: 3
- refusal_error: 1
- hallucination_error: 0
- legal_guarantee_error: 0
- answer_quality_error: 0
- ux_error: 0
- latency_error: 15
- exception_error: 0

## Failures By Topic

- annual_leave: 1/1 (100.0%)
- cdd_cdi: 1/1 (100.0%)
- dismissal: 1/1 (100.0%)
- labor_inspection: 1/1 (100.0%)
- no_written_contract: 2/2 (100.0%)
- preavis: 1/1 (100.0%)
- pregnancy_maternity: 2/2 (100.0%)
- resignation: 1/1 (100.0%)
- salary_unpaid: 1/1 (100.0%)
- sick_leave: 2/2 (100.0%)
- work_accident: 2/2 (100.0%)
- work_certificate: 1/1 (100.0%)

## Top Weak Topics

- pregnancy_maternity: 2/2 failed (100.0%)
- sick_leave: 2/2 failed (100.0%)
- no_written_contract: 2/2 failed (100.0%)
- work_accident: 2/2 failed (100.0%)
- salary_unpaid: 1/1 failed (100.0%)
- resignation: 1/1 failed (100.0%)
- annual_leave: 1/1 failed (100.0%)
- preavis: 1/1 failed (100.0%)
- cdd_cdi: 1/1 failed (100.0%)
- labor_inspection: 1/1 failed (100.0%)

## Question Style Distribution

- darija_arabic: 16
- arabizi: 0
- mixed_french_darija: 9
- typos: 0
- vague: 0
- angry: 0
- polite: 0
- incomplete_facts: 0
- emotional: 0
- legal_trap: 0

## Source Category Distribution

- code_travail: 20
- labor_inspection: 5
- work_accident: 4

## Failure Examples

- `stress_0001` [salary_unpaid/darija_arabic] ما خلصونيش هاد الشهر -> citation_error, latency_error: latency 69933ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0004` [resignation/darija_arabic] بغيت نستاقل وما عارفش المسطرة -> latency_error: latency 63586ms exceeded 30000ms
- `stress_0005` [annual_leave/darija_arabic] ما بغاوش يعطوني الكونجي السنوي -> latency_error: latency 43955ms exceeded 30000ms
- `stress_0008` [preavis/darija_arabic] شنو هو préavis فالخدمة؟ -> citation_error, latency_error: latency 87866ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0010` [cdd_cdi/darija_arabic] عندي CDD وكيجددوه كل مرة -> latency_error: latency 45390ms exceeded 30000ms
- `stress_0011` [pregnancy_maternity/darija_arabic] أنا حاملة والمشغل بغا يطردني -> latency_error: latency 91822ms exceeded 30000ms
- `stress_0057` [pregnancy_maternity/mixed_french_darija] svp j'ai un problème، أنا حاملة والمشغل بغا يطردني بغيت نفهم mes droits -> citation_error, latency_error: latency 59205ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0058` [sick_leave/mixed_french_darija] svp j'ai un problème، مرضت وما قدرتش نمشي للخدمة بغيت نفهم mes droits -> latency_error: latency 61520ms exceeded 30000ms
- `stress_0059` [no_written_contract/mixed_french_darija] svp j'ai un problème، خدام بلا عقد مكتوب بغيت نفهم mes droits -> refusal_error, conversation_routing_error: expected conversation type in ['labor_law'], got general_conversation; concrete labor-law question was refused
- `stress_0060` [work_accident/mixed_french_darija] svp j'ai un problème، طحت فالخدمة وتجرحت بغيت نفهم mes droits -> latency_error: latency 95168ms exceeded 30000ms
- `stress_0063` [labor_inspection/mixed_french_darija] svp j'ai un problème، بغيت نمشي لمفتشية الشغل بغيت نفهم mes droits -> latency_error: latency 46908ms exceeded 30000ms
- `stress_0064` [work_certificate/mixed_french_darija] svp j'ai un problème، ما بغاوش يعطوني شهادة العمل بغيت نفهم mes droits -> latency_error: latency 79648ms exceeded 30000ms
- `stress_0065` [dismissal/mixed_french_darija] svp j'ai un problème، طردوني من الخدمة بلا سبب مكتوب بغيت نفهم mes droits -> latency_error: latency 49741ms exceeded 30000ms
- `stress_0012` [sick_leave/darija_arabic] مرضت وما قدرتش نمشي للخدمة -> latency_error: latency 52884ms exceeded 30000ms
- `stress_0013` [no_written_contract/darija_arabic] خدام بلا عقد مكتوب -> latency_error: latency 54398ms exceeded 30000ms
- `stress_0014` [work_accident/darija_arabic] طحت فالخدمة وتجرحت -> latency_error: latency 52891ms exceeded 30000ms

## Recommended Fixes


### Critical

- Require returned legal sources and validate every rendered citation against them.
- Separate out-of-scope/fake-reference refusal rules from supported labor questions.

### High

- Expand routing coverage using the failed wording without changing unrelated routes.
- Prioritize manual review of the weakest topics: pregnancy_maternity, sick_leave, no_written_contract, work_accident, salary_unpaid.

### Medium

- Profile retrieval and Ollama generation for cases exceeding 30 seconds.

No fixes were applied by this run. Recommendations require review first.

## Output Files

- `stress_results_2000.jsonl`
- `stress_failures_2000.jsonl`
- `STRESS_EVALUATION_REPORT.md`
