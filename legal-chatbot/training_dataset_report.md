# Lmo7ami SFT Training Dataset Report

## Summary

- Total examples: 1500
- Train examples: 1200
- Validation examples: 150
- Test examples: 150
- Requires RAG examples: 1363
- Duplicate user input count: 0
- Validation errors: 0

## Examples Per Topic

- annual_leave: 68
- clarification_questions: 68
- cnss_non_declaration: 68
- contract_type: 68
- disciplinary_dismissal: 69
- dismissal: 69
- fake_article_refusal: 68
- greetings_identity: 69
- legal_guarantee_refusal: 68
- maternity_protection: 68
- no_written_contract: 68
- out_of_scope_refusal: 68
- overtime: 68
- practical_steps: 68
- preavis: 68
- resignation: 68
- salary_deduction: 68
- salary_unpaid: 68
- sick_leave: 68
- unclear_question: 69
- work_accident: 68
- work_certificate: 68

## Examples Per Intent

- annual_leave: 68
- cdd_cdi_question: 68
- clarification_questions: 68
- cnss_non_declaration: 68
- disciplinary_dismissal: 69
- dismissal_unclear: 69
- fake_article_refusal: 68
- greeting_identity: 69
- legal_guarantee_refusal: 68
- maternity_protection: 68
- no_written_contract: 68
- out_of_scope_refusal: 68
- overtime: 68
- practical_steps: 68
- preavis_question: 68
- resignation: 68
- salary_deduction: 68
- salary_unpaid: 68
- sick_leave: 68
- unclear_labor_question: 69
- work_accident: 68
- work_certificate: 68

## Validation Errors

- None

## Dataset Files

- Training directory: `data\training`
- Train split: `data/training/lmo7ami_sft_train.jsonl`
- Validation split: `data/training/lmo7ami_sft_val.jsonl`
- Test split: `data/training/lmo7ami_sft_test.jsonl`
- Manifest: `data/training/dataset_manifest.json`

## Recommended Next Step

Review a small random sample from each split manually, then wire these files into the QLoRA training job without bypassing RAG for legal facts.

## Manifest Snapshot

- Dataset version: 0.1.0
- Generator: `backend/build_sft_dataset.py`
- Format: jsonl chat messages
