# External Darija Import Report

## Summary

- Total configured sources: 2
- Clean examples written: 91921
- Raw directory: `data/external_darija/raw`
- Clean output: `data/external_darija/clean_darija_examples.jsonl`

## Examples Per Source

- doda: 91921

## Source Status

- doda (github_raw): ok
  - raw rows: 109544
  - candidates: 215339
  - kept: 91921
  - duplicates removed: 31285
  - filtered noisy: 92133
  - notes: Imported from GitHub archive fallback because raw URLs were empty or unavailable.
- atlaset (huggingface): failed
  - raw rows: 0
  - candidates: 0
  - kept: 0
  - duplicates removed: 0
  - filtered noisy: 0
  - errors: atlasia/Atlaset: Dataset 'atlasia/Atlaset' is a gated dataset on the Hub. You must be authenticated to access it.

## Guardrail

This dataset is external Darija text only. It has not been mixed with the legal SFT dataset and no training has been started.

## Recommended Next Step

Review a random sample, then decide whether it should be used for tokenizer/language adaptation or kept only as evaluation material.
