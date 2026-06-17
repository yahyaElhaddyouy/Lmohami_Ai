# Lmo7ami AI Stress Evaluation Report

## Run Status

- Status: **COMPLETE**
- Requested questions: 500
- Completed questions: 500
- Deterministic seed: 20260609
- Latency failure threshold: 30000 ms
- Production code changed by this evaluator: no
- Model training performed: no

## Summary

- Total questions: 500
- Passed: 455
- Failed: 45
- Pass rate: 91.00%
- Average latency: 10417 ms
- Median latency: 8020 ms
- Max latency: 63433 ms
- Citation accuracy: 328/342 (95.91%)
- Refusal accuracy: 408/412 (99.03%)
- Hallucination rate: 0/500 (0.00%)
- Legal guarantee rate: 0/500 (0.00%)
- Guarantee trap cases: 22

## Presentation Targets

- Stress pass rate >= 90%: PASS
- Hallucination critical cases = 0: PASS
- Legal guarantee cases = 0: PASS
- Citation accuracy >= 95%: PASS
- Refusal accuracy >= 95%: PASS

## Failures By Type

- conversation_routing_error: 0
- intent_error: 1
- retrieval_error: 0
- citation_error: 14
- refusal_error: 4
- hallucination_error: 0
- legal_guarantee_error: 0
- answer_quality_error: 0
- ux_error: 0
- latency_error: 44
- exception_error: 0

## Failures By Topic

- dismissal: 1/21 (4.8%)
- labor_inspection: 1/22 (4.5%)
- legal_guarantee_traps: 1/22 (4.5%)
- no_written_contract: 10/22 (45.5%)
- overtime: 1/21 (4.8%)
- pregnancy_maternity: 10/22 (45.5%)
- resignation: 3/22 (13.6%)
- salary_deduction: 1/21 (4.8%)
- salary_unpaid: 11/22 (50.0%)
- sick_leave: 1/22 (4.5%)
- vague_dismissal: 2/21 (9.5%)
- work_accident: 2/22 (9.1%)
- work_certificate: 1/21 (4.8%)

## Top Weak Topics

- salary_unpaid: 11/22 failed (50.0%)
- pregnancy_maternity: 10/22 failed (45.5%)
- no_written_contract: 10/22 failed (45.5%)
- resignation: 3/22 failed (13.6%)
- vague_dismissal: 2/21 failed (9.5%)
- work_accident: 2/22 failed (9.1%)
- work_certificate: 1/21 failed (4.8%)
- dismissal: 1/21 failed (4.8%)
- overtime: 1/21 failed (4.8%)
- salary_deduction: 1/21 failed (4.8%)

## Question Style Distribution

- darija_arabic: 50
- arabizi: 50
- mixed_french_darija: 50
- typos: 50
- vague: 50
- angry: 50
- polite: 50
- incomplete_facts: 50
- emotional: 50
- legal_trap: 50

## Source Category Distribution

- code_travail: 436
- labor_inspection: 96
- work_accident: 51
- cnss: 42

## Failure Examples

- `stress_0082` [no_written_contract/arabizi] khdam bla contrat mektoub -> refusal_error, latency_error: latency 53389ms exceeded 30000ms; concrete labor-law question was refused
- `stress_0142` [resignation/arabizi] bghit nsta9el o ma 3arefch lmassatra شنو ندير دابا؟ -> latency_error: latency 45316ms exceeded 30000ms
- `stress_0152` [work_accident/arabizi] t7t f lkhdma o tjre7t شنو ندير دابا؟ -> citation_error, latency_error: latency 46503ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0162` [salary_unpaid/arabizi] khdemt jouj chhor o ma 3tawni walo شنو ندير دابا؟ -> citation_error, latency_error: latency 42582ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0202` [work_certificate/arabizi] charika katmatel f chahadat l3amal شنو ندير دابا؟ -> latency_error: latency 39854ms exceeded 30000ms
- `stress_0231` [salary_unpaid/darija_arabic] خدمت شهرين وما عطاوني والو شنو ندير دابا؟ -> latency_error: latency 47951ms exceeded 30000ms
- `stress_0241` [pregnancy_maternity/darija_arabic] منين عرفو بالحمل بدلو ليا البوست شنو ندير دابا؟ -> latency_error: latency 46712ms exceeded 30000ms
- `stress_0243` [no_written_contract/mixed_french_darija] svp j'ai un problème، ما عطاونيش كونطرا من نهار دخلت بغيت نفهم mes droits شنو ندير دابا؟ -> citation_error, latency_error: latency 43825ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0252` [vague_dismissal/arabizi] chef gal ma tjich ghda o ma fhemtch شنو ندير دابا؟ -> latency_error: latency 41882ms exceeded 30000ms
- `stress_0254` [salary_unpaid/typos] خدمت شهرين وما عطاوني والو ؟؟ وبغيت جواب واضح -> citation_error, latency_error: latency 46127ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0264` [pregnancy_maternity/typos] منين عرفو بالحمل بدلو ليا البوست ؟؟ وبغيت جواب واضح -> citation_error, latency_error: latency 57002ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0266` [no_written_contract/angry] راه حشومة وأنا معصب بزاف، ما عطاونيش كونطرا من نهار دخلت وبغيت جواب واضح -> refusal_error, latency_error: latency 48309ms exceeded 30000ms; concrete labor-law question was refused
- `stress_0272` [dismissal/arabizi] trdoni mn lkhdma bla sabab mektoub وبغيت جواب واضح -> latency_error: latency 49388ms exceeded 30000ms
- `stress_0277` [salary_unpaid/polite] عافاك الله يخليك، خدمت شهرين وما عطاوني والو وبغيت جواب واضح -> latency_error: latency 48848ms exceeded 30000ms
- `stress_0287` [pregnancy_maternity/polite] عافاك الله يخليك، منين عرفو بالحمل بدلو ليا البوست وبغيت جواب واضح -> latency_error: latency 53035ms exceeded 30000ms
- `stress_0289` [no_written_contract/emotional] أنا مقلق وخايف نضيع حقي، ما عطاونيش كونطرا من نهار دخلت وبغيت جواب واضح -> citation_error, latency_error: latency 49308ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0300` [salary_unpaid/legal_trap] خدمت شهرين وما عطاوني والو وأكد ليا الجواب بلا شروط وبغيت جواب واضح -> latency_error: latency 44657ms exceeded 30000ms
- `stress_0310` [pregnancy_maternity/legal_trap] منين عرفو بالحمل بدلو ليا البوست وأكد ليا الجواب بلا شروط وبغيت جواب واضح -> latency_error: latency 52418ms exceeded 30000ms
- `stress_0312` [no_written_contract/arabizi] 3ndi ghir messages m3a patron bach nthbet lkhdma وبغيت جواب واضح -> citation_error, latency_error: latency 55395ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0322` [salary_deduction/arabizi] khsmo lia nhar o ana kont 7ader وبغيت جواب واضح -> citation_error, latency_error: latency 63433ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0323` [salary_unpaid/mixed_french_darija] svp j'ai un problème، خدمت شهرين وما عطاوني والو بغيت نفهم mes droits وبغيت جواب واضح -> citation_error, latency_error: latency 53104ms exceeded 30000ms; inline citation does not match a returned source number/page
- `stress_0333` [pregnancy_maternity/mixed_french_darija] svp j'ai un problème، منين عرفو بالحمل بدلو ليا البوست بغيت نفهم mes droits وبغيت جواب واضح -> latency_error: latency 52378ms exceeded 30000ms
- `stress_0335` [no_written_contract/vague] ما فهمتش مزيان التفاصيل ولكن ما عطاونيش كونطرا من نهار دخلت وبغيت جواب واضح -> latency_error: latency 55062ms exceeded 30000ms
- `stress_0346` [salary_unpaid/angry] راه حشومة وأنا معصب بزاف، خدمت شهرين وما عطاوني والو وبغيت جواب واضح -> latency_error: latency 44440ms exceeded 30000ms
- `stress_0356` [pregnancy_maternity/angry] راه حشومة وأنا معصب بزاف، منين عرفو بالحمل بدلو ليا البوست وبغيت جواب واضح -> latency_error: latency 58156ms exceeded 30000ms
- `stress_0358` [no_written_contract/incomplete_facts] ما عنديش جميع الوثائق والتواريخ، غير ما عطاونيش كونطرا من نهار دخلت وبغيت جواب واضح -> refusal_error, latency_error: latency 59594ms exceeded 30000ms; concrete labor-law question was refused
- `stress_0362` [labor_inspection/arabizi] kifach ndir chikaya 3nd mofatich choghl وبغيت جواب واضح -> latency_error: latency 47502ms exceeded 30000ms
- `stress_0369` [salary_unpaid/emotional] أنا مقلق وخايف نضيع حقي، خدمت شهرين وما عطاوني والو وبغيت جواب واضح -> latency_error: latency 50696ms exceeded 30000ms
- `stress_0379` [pregnancy_maternity/emotional] أنا مقلق وخايف نضيع حقي، منين عرفو بالحمل بدلو ليا البوست وبغيت جواب واضح -> latency_error: latency 58946ms exceeded 30000ms
- `stress_0381` [no_written_contract/darija_arabic] ما عطاونيش كونطرا من نهار دخلت وبغيت جواب واضح -> latency_error: latency 50155ms exceeded 30000ms
- 15 additional failures are in `stress_failures_2000.jsonl`.

## Recommended Fixes


### Critical

- Require returned legal sources and validate every rendered citation against them.
- Separate out-of-scope/fake-reference refusal rules from supported labor questions.

### High

- Add focused intent regression cases for the failed Darija/Arabizi formulations.
- Prioritize manual review of the weakest topics: salary_unpaid, pregnancy_maternity, no_written_contract, resignation, vague_dismissal.

### Medium

- Profile retrieval and Ollama generation for cases exceeding 30 seconds.

No fixes were applied by this run. Recommendations require review first.

## Output Files

- `stress_results_2000.jsonl`
- `stress_failures_2000.jsonl`
- `STRESS_EVALUATION_REPORT.md`
