# Darija Comprehension Training Start Report

## Summary

- External Darija import: complete
- Clean external Darija examples: 91,921
- Broad Darija SFT examples: 10,000
- Train split: 8,000
- Validation split: 1,000
- Test split: 1,000
- Legal SFT mixed in: no
- Training started: no

## Why Training Did Not Start

- Python 3.11 has CPU-only PyTorch: CUDA is not available from `torch`.
- `peft` is missing.
- `bitsandbytes` is missing.
- Installing `peft bitsandbytes` timed out before completion.
- The local GPU is an RTX 2050 with 4 GB VRAM, so QLoRA for `qwen2.5:7b` is not realistic on this machine.

## Files Created

- `backend/build_darija_comprehension_sft.py`
- `backend/validate_darija_comprehension_sft.py`
- `backend/train_darija_qlora.py`
- `backend/training_requirements.txt`
- `data/training/darija_comprehension_train.jsonl`
- `data/training/darija_comprehension_val.jsonl`
- `data/training/darija_comprehension_test.jsonl`
- `data/training/darija_comprehension_manifest.json`
- `darija_comprehension_training_report.md`

## Guardrail

This stage is for Moroccan Darija comprehension and off-topic routing. Legal facts, citations, and law-specific answers must still come from RAG.

## Recommended Next Step

Create a clean Python 3.11 training environment with CUDA-enabled PyTorch, `peft`, and `bitsandbytes`, then run:

```powershell
cd backend
python train_darija_qlora.py --preflight
python train_darija_qlora.py --model Qwen/Qwen2.5-0.5B-Instruct --max-steps 1000
```
