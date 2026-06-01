"""QLoRA/LoRA training entrypoint for broad Darija comprehension.

The default model is intentionally small. The current app can still use a
larger Ollama model for inference, but this script is for producing a reviewed
adapter on hardware that can actually support training.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TRAIN = PROJECT_DIR / "data" / "training" / "darija_comprehension_train.jsonl"
DEFAULT_VAL = PROJECT_DIR / "data" / "training" / "darija_comprehension_val.jsonl"
DEFAULT_OUTPUT = PROJECT_DIR / "models" / "lmo7ami-darija-comprehension-adapter"


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def preflight(require_bitsandbytes: bool = True) -> tuple[bool, list[str]]:
    required = ["torch", "transformers", "datasets", "accelerate", "peft"]
    if require_bitsandbytes:
        required.append("bitsandbytes")
    missing = [name for name in required if not module_available(name)]
    blockers: list[str] = []
    lines = [
        "Darija QLoRA preflight",
        f"- python: {platform.python_version()} ({sys.executable})",
        f"- platform: {platform.platform()}",
    ]
    if module_available("torch"):
        import torch

        lines.append(f"- torch: {torch.__version__}")
        cuda_available = torch.cuda.is_available()
        lines.append(f"- cuda available: {cuda_available}")
        if torch.cuda.is_available():
            lines.append(f"- gpu: {torch.cuda.get_device_name(0)}")
            props = torch.cuda.get_device_properties(0)
            lines.append(f"- gpu memory: {props.total_memory / (1024**3):.1f} GB")
        elif require_bitsandbytes:
            blockers.append("CUDA is not available in this Python environment, so QLoRA cannot use the NVIDIA GPU.")
    else:
        lines.append("- torch: missing")

    for name in ("transformers", "datasets", "accelerate", "peft", "bitsandbytes"):
        lines.append(f"- {name}: {'ok' if module_available(name) else 'missing'}")

    if missing:
        lines.append("")
        lines.append("Missing training dependencies:")
        for name in missing:
            lines.append(f"- {name}")
    if blockers:
        lines.append("")
        lines.append("Training blockers:")
        for blocker in blockers:
            lines.append(f"- {blocker}")
    if missing or blockers:
        lines.append("")
        lines.append("Create a Python 3.10/3.11 training env, then install:")
        lines.append("pip install -r backend/training_requirements.txt")
        return False, lines
    return True, lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Darija comprehension LoRA/QLoRA adapter.")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--train-file", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--val-file", type=Path, default=DEFAULT_VAL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--max-length", type=int, default=768)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit quantization.")
    parser.add_argument("--preflight", action="store_true", help="Check training environment and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Load dataset/model config but do not train.")
    return parser.parse_args()


def render_messages(tokenizer: object, messages: list[dict[str, str]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)  # type: ignore[attr-defined]
    chunks = []
    for message in messages:
        chunks.append(f"{message['role']}: {message['content']}")
    return "\n".join(chunks)


def read_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def main() -> int:
    args = parse_args()
    use_4bit = not args.no_4bit
    ok, report_lines = preflight(require_bitsandbytes=use_4bit)
    print("\n".join(report_lines))
    if args.preflight:
        return 0 if ok else 2
    if not ok:
        return 2

    if not args.train_file.exists() or not args.val_file.exists():
        print("Training dataset is missing. Run build_darija_comprehension_sft.py first.")
        return 2

    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    print("Training plan")
    print(f"- model: {args.model}")
    print(f"- train rows: {read_jsonl_count(args.train_file)}")
    print(f"- validation rows: {read_jsonl_count(args.val_file)}")
    print(f"- output: {args.output_dir}")
    print(f"- max steps: {args.max_steps}")
    print(f"- 4-bit: {use_4bit}")
    print("Guardrail: legal facts still come from RAG; this adapter is for Darija comprehension/routing.")
    if args.dry_run:
        print("Dry run requested; no training started.")
        return 0

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization_config = None
    model_kwargs: dict[str, object] = {"trust_remote_code": True}
    if use_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model_kwargs.update({"quantization_config": quantization_config, "device_map": "auto"})

    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    if use_4bit:
        model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)

    dataset = load_dataset(
        "json",
        data_files={"train": str(args.train_file), "validation": str(args.val_file)},
    )

    def tokenize(batch: dict[str, list[object]]) -> dict[str, object]:
        texts = [render_messages(tokenizer, messages) for messages in batch["messages"]]  # type: ignore[arg-type]
        tokenized = tokenizer(texts, max_length=args.max_length, truncation=True)
        tokenized["labels"] = [list(input_ids) for input_ids in tokenized["input_ids"]]
        return tokenized

    tokenized = dataset.map(tokenize, batched=True, remove_columns=dataset["train"].column_names)
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        max_steps=args.max_steps,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=100,
        save_steps=100,
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        report_to=[],
        remove_unused_columns=False,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "training_guardrails.json").write_text(
        json.dumps(
            {
                "purpose": "Darija comprehension and off-topic routing",
                "legal_facts_source": "RAG only",
                "base_model": args.model,
                "train_file": str(args.train_file.relative_to(PROJECT_DIR)),
                "validation_file": str(args.val_file.relative_to(PROJECT_DIR)),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    print(f"Training complete. Adapter saved to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
