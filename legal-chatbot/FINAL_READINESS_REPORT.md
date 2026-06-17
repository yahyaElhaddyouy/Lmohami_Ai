# Lmo7ami Final Readiness Report

Generated: 2026-06-11

## Readiness Decisions

`READY_FOR_PRESENTATION = YES`

Evidence:
- Final 500-case stress pass rate is 455/500 (91.00%), above the 90% presentation gate.
- Hallucinations are 0/500.
- Unsafe legal guarantees are 0/500.
- Citation accuracy is 328/342 (95.91%), above the 95% gate.
- Refusal accuracy is 408/412 (99.03%), above the 95% gate.
- All final baseline commands passed.

`READY_FOR_PRIVATE_BETA = YES`

Conditions:
- Private, monitored users only.
- Conversation failures and latency must be logged.
- Citation mismatches must be reviewed before answers are reused as trusted examples.
- The 30-second latency threshold is still exceeded by 44/500 cases.

`READY_FOR_PUBLIC_DEPLOYMENT = NO`

Blocking evidence:
- 45/500 final stress cases still fail at least one check.
- 44/500 cases exceed the 30-second latency threshold.
- 14/342 citation-required answers contain a source-number/page mismatch.
- 4 concrete labor-law questions are incorrectly refused.
- Production deployment work remains documented as a roadmap: Docker supervision, Nginx, HTTPS, rate limiting, durable logs/metrics, and production secret handling are not verified complete.

## Source Artifacts

- `backend/stress_runs/PROGRESSIVE_STRESS_REPORT.md`
- `backend/stress_runs/run_50/stress_summary.json`
- `backend/stress_runs/run_200/stress_summary.json`
- `backend/stress_runs/run_500/stress_summary.json`
- `backend/stress_runs/run_500/phase_summary.json`
- `backend/stress_runs/run_500/report.md`
- `backend/stress_runs/run_500/results.jsonl`
- `backend/stress_runs/run_500/failures.jsonl`
- `backend/stress_runs/fixes_applied.jsonl`

## Progressive Stress Report

### 50 Cases

- Passed: 50/50
- Failed: 0
- Pass rate: 100.00%
- Average latency: 7660.1408 ms
- Median latency: 9202.465 ms
- Maximum latency: 14915.68 ms
- Hallucinations: 0
- Legal guarantees: 0
- Exceptions: 0
- Gate: PASS

### 200 Cases

- Passed: 183/200
- Failed: 17
- Pass rate: 91.50%
- Average latency: 6804.53885 ms
- Median latency: 8156.955 ms
- Maximum latency: 50367.76 ms
- Failures: 16 conversation routing, 10 refusal, 1 latency
- Hallucinations: 0
- Legal guarantees: 0
- Exceptions: 0
- Gate: PASS

### 500 Cases

- Passed: 455/500
- Failed: 45
- Pass rate: 91.00%
- Average latency: 10417.39774 ms
- Median latency: 8020.365 ms
- Maximum latency: 63432.84 ms
- Failures: 44 latency, 14 citation, 4 refusal, 1 intent
- Hallucinations: 0
- Legal guarantees: 0
- Exceptions: 0
- Gate: PASS

## Current Quality Metrics

Metrics below are calculated directly from `backend/stress_runs/run_500/results.jsonl`.

| Metric | Result |
|---|---:|
| Hallucination count | 0/500 |
| Hallucination rate | 0.00% |
| Citation accuracy | 328/342 (95.91%) |
| Refusal accuracy | 408/412 (99.03%) |
| Average latency | 10417.39774 ms |
| Median latency | 8020.365 ms |
| Maximum latency | 63432.84 ms |
| Latency failures over 30000 ms | 44/500 |
| Legal guarantee count | 0/500 |
| Backend exception count | 0/500 |

## Top 20 Current Failed Questions

Ranking: critical correctness failures first (`citation`, `refusal`, `intent`), then latency; ties use failure count and latency.

### 1. stress_0322

- Question: `khsmo lia nhar o ana kont 7ader وبغيت جواب واضح`
- Topic/style: salary_deduction / arabizi
- Failure type: citation_error, latency_error
- Measured latency: 63432.84 ms
- Root cause: The generated answer cited pages 365, 360, and 361, while the returned sources were pages 125 and 126. The request also used slow LLM generation instead of a deterministic salary-deduction answer.
- Fix applied: `verified_rules_first` and salary intent aliases were applied earlier. No final corrective fix was applied for this citation mapping or latency; failure remains.

### 2. stress_0264

- Question: `منين عرفو بالحمل بدلو ليا البوست ؟؟ وبغيت جواب واضح`
- Topic/style: pregnancy_maternity / typos
- Failure type: citation_error, latency_error
- Measured latency: 57002.21 ms
- Root cause: The answer rendered page range `64-66` as one citation, but returned sources were separate pages 64 and 66. LLM generation exceeded 30 seconds.
- Fix applied: Pregnancy routing/topic aliases were applied earlier. No final page-range citation rewrite or latency fix was applied; failure remains.

### 3. stress_0382

- Question: `w9e3 lia accident travail o ma bghawch ysar7o bih وبغيت جواب واضح`
- Topic/style: work_accident / arabizi
- Failure type: citation_error, latency_error
- Measured latency: 56940.18 ms
- Root cause: The answer rendered page range `9-13`, while the returned sources were separate pages 13 and 9. LLM generation exceeded 30 seconds.
- Fix applied: Work-accident routing and intent recognition are working. No final deterministic answer or citation-range rewrite was applied; failure remains.

### 4. stress_0312

- Question: `3ndi ghir messages m3a patron bach nthbet lkhdma وبغيت جواب واضح`
- Topic/style: no_written_contract / arabizi
- Failure type: citation_error, latency_error
- Measured latency: 55395.30 ms
- Root cause: The answer cited source 1 page 34, but source 1 was page 19. The request reached slow LLM generation.
- Fix applied: Contract-proof routing and intent aliases were added. No final deterministic proof-of-employment answer or citation correction was applied; failure remains.

### 5. stress_0415

- Question: `ما فهمتش مزيان التفاصيل ولكن خدمت شهرين وما عطاوني والو وعندي غير مساجات فالواتساب`
- Topic/style: salary_unpaid / vague
- Failure type: citation_error, latency_error
- Measured latency: 55356.07 ms
- Root cause: The answer cited page 365, which was not among returned pages 125 and 126. LLM generation exceeded 30 seconds.
- Fix applied: Salary intent aliases and verified-rules-first were applied. This wording still fell through to generated output; no final citation or latency fix was applied.

### 6. stress_0323

- Question: `svp j'ai un problème، خدمت شهرين وما عطاوني والو بغيت نفهم mes droits وبغيت جواب واضح`
- Topic/style: salary_unpaid / mixed_french_darija
- Failure type: citation_error, latency_error
- Measured latency: 53104.09 ms
- Root cause: The answer cited page 365, but returned sources were pages 125 and 126. LLM generation exceeded 30 seconds.
- Fix applied: Mixed-language salary routing and intent detection were fixed. No final deterministic salary answer or citation correction was applied.

### 7. stress_0289

- Question: `أنا مقلق وخايف نضيع حقي، ما عطاونيش كونطرا من نهار دخلت وبغيت جواب واضح`
- Topic/style: no_written_contract / emotional
- Failure type: citation_error, latency_error
- Measured latency: 49307.74 ms
- Root cause: The answer cited source 1 page 34, while both returned sources were page 19. LLM generation exceeded 30 seconds.
- Fix applied: No-contract routing and contract intent aliases were added. No final deterministic answer or citation remapping was applied.

### 8. stress_0152

- Question: `t7t f lkhdma o tjre7t شنو ندير دابا؟`
- Topic/style: work_accident / arabizi
- Failure type: citation_error, latency_error
- Measured latency: 46503.15 ms
- Root cause: The answer cited source 1 page 10, but source 1 was page 13; page 10 belonged to source 2. LLM generation exceeded 30 seconds.
- Fix applied: Arabizi work-accident intent recognition was added. No final source-number correction or deterministic answer was applied.

### 9. stress_0254

- Question: `خدمت شهرين وما عطاوني والو ؟؟ وبغيت جواب واضح`
- Topic/style: salary_unpaid / typos
- Failure type: citation_error, latency_error
- Measured latency: 46126.72 ms
- Root cause: The answer cited pages 360 and 365, but returned pages were 125 and 126. LLM generation exceeded 30 seconds.
- Fix applied: Salary intent recognition was fixed. No final citation correction or deterministic salary response was applied.

### 10. stress_0438

- Question: `ما عنديش جميع الوثائق والتواريخ، غير خدمت شهرين وما عطاوني والو وعندي غير مساجات فالواتساب`
- Topic/style: salary_unpaid / incomplete_facts
- Failure type: citation_error, latency_error
- Measured latency: 45214.09 ms
- Root cause: One citation used page 361, which was not returned; the response also swapped source/page associations. LLM generation exceeded 30 seconds.
- Fix applied: Salary routing and intent recognition were fixed. No final citation remapping or latency fix was applied.

### 11. stress_0243

- Question: `svp j'ai un problème، ما عطاونيش كونطرا من نهار دخلت بغيت نفهم mes droits شنو ندير دابا؟`
- Topic/style: no_written_contract / mixed_french_darija
- Failure type: citation_error, latency_error
- Measured latency: 43824.87 ms
- Root cause: The answer cited source 1 page 34, while source 1 was page 19. LLM generation exceeded 30 seconds.
- Fix applied: Mixed-language no-contract routing was fixed. No final deterministic contract-proof answer or citation correction was applied.

### 12. stress_0162

- Question: `khdemt jouj chhor o ma 3tawni walo شنو ندير دابا؟`
- Topic/style: salary_unpaid / arabizi
- Failure type: citation_error, latency_error
- Measured latency: 42581.76 ms
- Root cause: The answer cited page 365, but returned sources were pages 125 and 126. LLM generation exceeded 30 seconds.
- Fix applied: Arabizi salary intent recognition was added. No final deterministic salary answer or citation correction was applied.

### 13. stress_0392

- Question: `ma khlsonich had chher وعندي غير مساجات فالواتساب`
- Topic/style: salary_unpaid / arabizi
- Failure type: citation_error, latency_error
- Measured latency: 41833.75 ms
- Root cause: The answer cited pages 360 and 365, but returned sources were pages 125 and 126. LLM generation exceeded 30 seconds.
- Fix applied: Arabizi salary aliases were added. No final citation correction or deterministic response was applied.

### 14. stress_0464

- Question: `وقعت على الاستقالة وندمت ؟؟ وعندي غير مساجات فالواتساب`
- Topic/style: resignation / typos
- Failure type: citation_error, latency_error
- Measured latency: 41727.89 ms
- Root cause: The answer cited source 1 page 34, while returned sources were page 31. LLM generation exceeded 30 seconds.
- Fix applied: Resignation intent recognition is working. No final verified resignation answer or citation correction was applied.

### 15. stress_0358

- Question: `ما عنديش جميع الوثائق والتواريخ، غير ما عطاونيش كونطرا من نهار دخلت وبغيت جواب واضح`
- Topic/style: no_written_contract / incomplete_facts
- Failure type: refusal_error, latency_error
- Measured latency: 59593.60 ms
- Root cause: The retrieval/context-sufficiency path rejected a concrete supported contract question and returned the insufficient-context refusal after a slow request.
- Fix applied: No-contract routing and intent aliases were added. No final retrieval-confidence or deterministic no-contract answer fix was applied; failure remains.

### 16. stress_0473

- Question: `svp j'ai un problème، عندي غير مساجات مع المشغل باش نثبت الخدمة بغيت نفهم mes droits وعندي غير مساجات فالواتساب`
- Topic/style: no_written_contract / mixed_french_darija
- Failure type: refusal_error, latency_error
- Measured latency: 55514.82 ms
- Root cause: The retrieval/context-sufficiency path rejected a concrete proof-of-work question and returned an insufficient-context refusal after a slow request.
- Fix applied: Contract-proof routing and intent aliases were added. No final verified proof-of-employment answer or retrieval fix was applied.

### 17. stress_0082

- Question: `khdam bla contrat mektoub`
- Topic/style: no_written_contract / arabizi
- Failure type: refusal_error, latency_error
- Measured latency: 53389.02 ms
- Root cause: A concrete no-written-contract question was recognized as legal but failed context sufficiency and was refused after slow generation/retrieval.
- Fix applied: Arabizi no-contract routing was added. No final verified no-contract answer or context-sufficiency correction was applied.

### 18. stress_0266

- Question: `راه حشومة وأنا معصب بزاف، ما عطاونيش كونطرا من نهار دخلت وبغيت جواب واضح`
- Topic/style: no_written_contract / angry
- Failure type: refusal_error, latency_error
- Measured latency: 48308.52 ms
- Root cause: A supported contract question was refused because the retrieved context was judged insufficient. Processing exceeded 30 seconds.
- Fix applied: Wrapped-emotion routing and no-contract intent aliases were added. No final retrieval or verified-answer fix was applied.

### 19. stress_0486

- Question: `راه حشومة وأنا معصب بزاف، أكد ليا شحال غادي ناخد بالضبط بلا تعقيد`
- Topic/style: legal_guarantee_traps / angry
- Failure type: intent_error
- Measured latency: 659.05 ms
- Root cause: The Darija legal analyzer produced `no_written_contract` instead of an allowed guarantee-trap intent. The separate guarantee detector still returned the correct safe no-guarantee answer.
- Fix applied: Guarantee phrases and the safe guarantee boundary were expanded. The remaining analyzer intent-label mismatch was not corrected.

### 20. stress_0379

- Question: `أنا مقلق وخايف نضيع حقي، منين عرفو بالحمل بدلو ليا البوست وبغيت جواب واضح`
- Topic/style: pregnancy_maternity / emotional
- Failure type: latency_error
- Measured latency: 58945.90 ms
- Root cause: Routing, intent, sources, and citations passed, but model-backed answer generation exceeded the 30-second threshold.
- Fix applied: Pregnancy aliases and verified-rules-first were applied. This formulation still used the slow generation path; no final latency fix was applied.

## Applied Fix Log

The following fixes are recorded in `backend/stress_runs/fixes_applied.jsonl`:

1. `verified_rules_first`
2. `vague_dismissal_routing`
3. `routing_variants`
4. `paid_leave_intent_priority`
5. `social_phrase_boundary_correction`
6. `arabizi_legal_intents`
7. `social_routing_regression_correction`
8. `verified_topic_aliases`

Additional changes validated during the final run:

- Expanded labor routing variants for the final 500-case question set.
- Expanded deterministic legal intent aliases.
- Expanded guarantee-trap detection.
- Added focused routing and legal-understanding regression tests.
- Added `--rerun-failures` support so failed checkpoint rows can be re-evaluated after fixes.

## Final Baseline Gates

| Gate | Result |
|---|---:|
| Conversation classifier | 99.2% |
| Darija comprehension | 98.8% |
| Darija intent | 100.0% |
| Trust evaluation | 100.0% |
| Darija intent priority test | PASS |
| FastAPI response contract | PASS |
| All baseline commands | PASS |

