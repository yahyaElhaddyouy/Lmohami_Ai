# Lmo7ami AI Test Report

Date: 2026-05-28

## Tests Run

- `python evaluate_darija_intent.py`
- `python evaluate_trust.py --report trust_report.json`
- Manual `ask_chatbot(..., return_sources=True)` checks for:
  1. `واش الحامل عندها حماية من الطرد؟`
  2. `طردوني وأنا حامل`
  3. `قالو ليا ما تبقاش تجي`
  4. `ما خلصنيش الباطرون`
  5. `كيشدو ليا CNSS ولكن ما مصرحينش بيا`
  6. `أنا وقع ليا حادث داخل الخدمة شنو ندير؟`
  7. `شنو كتقول المادة 999؟`
  8. `كيفاش ندير طلاق اتفاقي؟`
  9. `السلام عليكم`
  10. `شكرا`
- `python -m py_compile rag.py darija_intent.py evaluate_darija_intent.py main.py evaluate_trust.py test_darija_intent_priority.py`
- `python -m unittest test_darija_intent_priority.py`

Note: one first manual attempt was discarded because a PowerShell here-string converted Arabic input to `???`. The manual checks were rerun with Unicode-safe input before classifying failures.

## Baseline Results

- Darija intent evaluation: `100/100 (100.0%)`, PASS.
- Trust evaluation: `105/105 (100%)`, PASS.
- Pregnancy priority checks detected `maternity_protection` correctly.

## Failures Found

- Case 6, `أنا وقع ليا حادث داخل الخدمة شنو ندير؟`
  - Classification: `retrieval_error`, then `answer_quality_error`.
  - Symptom: intent was correct (`work_accident_compensation`), but retrieval prioritized CNSS chunks and returned a CNSS non-declaration answer.
  - Cause: generic `تصريح` and query expansion containing `CNSS` made accident questions look CNSS-related.

- Case 5, `كيشدو ليا CNSS ولكن ما مصرحينش بيا`
  - Classification: `ux_error`.
  - Symptom: uncertainty text appeared before the required legal-answer structure.

- Case 3, `قالو ليا ما تبقاش تجي`
  - Classification: `ux_error`.
  - Symptom: generic dismissal wording said `إلا قالو ليك طردوني`, which was unnatural for the user phrasing.

## Fixes Applied

- `rag.py`
  - Added explicit CNSS detection so standalone `تصريح` no longer triggers CNSS behavior.
  - Added source-category scoring to prioritize `work_accident` documents for accident questions and CNSS documents only for explicit CNSS questions.
  - Updated verified source subset logic to keep `work_accident` chunks when available.
  - Restricted CNSS verified rules to explicit CNSS questions.
  - Folded uncertainty prefixes into `فهمت الحالة` instead of placing them before the answer structure.
  - Cleaned the generic dismissal phrase for `ما تبقاش تجي` style questions.

No FastAPI response shape, Flutter contract, or `ask_chatbot()` signature changes were made.

## Final Results

- Darija intent evaluation: `100/100 (100.0%)`, PASS.
- Trust evaluation: `105/105 (100%)`, PASS.
- Pregnancy unit test: PASS.
- Final manual checks:
  - Pregnancy questions: `maternity_protection`, legal citations present.
  - Dismissal and salary questions: legal citations present.
  - CNSS question: CNSS sources retrieved.
  - Work accident question: `work_accident` sources retrieved.
  - Unknown article and divorce question: refused without citations.
  - Greeting and thanks: short replies without citations.

## Remaining Risks

- Some deterministic legal answers still use a generic `فهمت الحالة` sentence. It is safe, but could be made more topic-specific later.
- Trust evaluation is strong on the current test set, but real-world Moroccan Darija phrasing will need continued expansion.
- Legal correctness remains limited by indexed source quality and retrieval coverage.
