# Darija Comprehension Training Dataset Report

## Summary

- Total examples: 10000
- Train examples: 8000
- Validation examples: 1000
- Test examples: 1000
- Legal facts included: no
- Mixed into legal SFT dataset: no

## Examples Per Mode

- meaning_with_boundary: 9998
- scope_router: 2

## Top Raw Sources

- `data/external_darija/raw/doda/sentences/sentences.csv`: 6668
- `data/external_darija/raw/doda/x-tra/shorts.csv`: 3023
- `data/external_darija/raw/doda/syntactic categories/nouns.csv`: 131
- `data/external_darija/raw/doda/syntactic categories/adjectives.csv`: 79
- `data/external_darija/raw/doda/syntactic categories/verbs.csv`: 63
- `data/external_darija/raw/doda/semantic categories/food.csv`: 16
- `data/external_darija/raw/doda/syntactic categories/adverbs.csv`: 11
- `data/external_darija/raw/doda/semantic categories/health.csv`: 4
- `data/external_darija/raw/doda/semantic categories/family.csv`: 3
- `data/external_darija/raw/doda/x-tra/idioms.csv`: 2

## Recommended Next Step

Run `python train_darija_qlora.py --preflight` from `backend/`. Only start real QLoRA after the ML stack and GPU target are confirmed.
