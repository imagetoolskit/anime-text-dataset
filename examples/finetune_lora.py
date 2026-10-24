"""LoRA fine-tuning on the Large Anime Text Dataset.

Usage:
    python examples/finetune_lora.py \
        --model HuggingFaceTB/SmolLM2-1.7B-Instruct \
        --data exports/instructions.jsonl \
        --split train --epochs 2 \
        --output runs/anime-lora

Optionally pass --qa exports/qa.jsonl to mix in QA pairs, and --qlora to
load the base in 4-bit (larger models, smaller GPUs).

This trains LoRA adapters (not a full-model update) and writes them to
<output>/final, which is what `peft.PeftModel.from_pretrained` expects.
"""
import argparse
import json

from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer


def load_rows(data_path, split, qa_path=None, limit=100_000):
    """Return (user, answer) pairs from one or two JSONL shards."""
    pairs = []
    paths = [data_path] if qa_path is None else [data_path, qa_path]
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                d = json.loads(line)
                if d.get("split") != split:
                    continue
                user = d.get("question") or d.get("instruction")
                answer = d.get("answer") or d.get("output")
                if user and answer:
                    pairs.append((user, answer))
                if len(pairs) >= limit:
                    return pairs
    return pairs


def render(tokenizer, user, answer):
    messages = [{"role": "user", "content": user},
                {"role": "assistant", "content": answer}]
    if tokenizer.chat_template:
        return tokenizer.apply_chat_template(messages, tokenize=False)
    return f"### Instruction:\n{user}\n\n### Response:\n{answer}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="HuggingFaceTB/SmolLM2-1.7B-Instruct")
    ap.add_argument("--data", required=True, help="JSONL with a 'split' field")
    ap.add_argument("--qa", default=None, help="optional QA JSONL to mix in")
    ap.add_argument("--split", default="train")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--limit", type=int, default=100_000)
    ap.add_argument("--output", default="runs/anime-lora")
    ap.add_argument("--qlora", action="store_true", help="load base in 4-bit")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    pairs = load_rows(args.data, args.split, args.qa, args.limit)
    if not pairs:
        raise SystemExit(f"no rows with split={args.split!r} in {args.data}")
    ds = Dataset.from_list(
        [{"text": render(tok, user, answer)} for user, answer in pairs])

    kwargs = {}
    if args.qlora:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype="float16")
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto", **kwargs)

    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                      target_modules="all-linear", task_type="CAUSAL_LM")
    cfg = SFTConfig(output_dir=args.output, per_device_train_batch_size=2,
                    gradient_accumulation_steps=8, num_train_epochs=args.epochs,
                    learning_rate=2e-4, max_length=1024, report_to="none")
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds,
                         processing_class=tok, peft_config=lora)
    trainer.train()
    trainer.save_model(f"{args.output}/final")
    print(f"saved LoRA adapters to {args.output}/final")


if __name__ == "__main__":
    main()
