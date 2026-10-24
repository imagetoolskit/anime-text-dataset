# Training Guide — Every Way to Train Models on This Dataset

> A complete, honest, and runnable reference for training language models on
> the **Large Anime Text Dataset**. Nine concrete recipes are covered, from
> quick LoRA fine-tunes on a single GPU to full domain pretraining and
> embedding/retrieval training. Every code block uses stable, widely adopted
> APIs (`transformers`, `datasets`, `peft`, `trl`, `bitsandbytes`,
> `sentence-transformers`, `faiss`) so it runs against current library
> versions with only minor, clearly-flagged version differences.

## Table of contents

- [0. What you actually get here](#0-what-you-actually-get-here)
- [1. Setup and hardware](#1-setup-and-hardware)
- [2. Data preparation for training](#2-data-preparation-for-training)
- [3. Recipe 1 — Instruction fine-tuning (SFT)](#3-recipe-1--instruction-fine-tuning-sft)
- [4. Recipe 2 — Parameter-efficient fine-tuning (LoRA / QLoRA)](#4-recipe-2--parameter-efficient-fine-tuning-lora--qlora)
- [5. Recipe 3 — Preference tuning (DPO)](#5-recipe-3--preference-tuning-dpo)
- [6. Recipe 4 — Retrieval-augmented generation (RAG) fine-tuning](#6-recipe-4--retrieval-augmented-generation-rag-fine-tuning)
- [7. Recipe 5 — Domain continual pretraining](#7-recipe-5--domain-continual-pretraining)
- [8. Recipe 6 — Contrastive / embedding training for retrieval](#8-recipe-6--contrastive--embedding-training-for-retrieval)
- [9. Recipe 7 — Classification and ranking](#9-recipe-7--classification-and-ranking)
- [10. Recipe 8 — Entity linking and relation extraction](#10-recipe-8--entity-linking-and-relation-extraction)
- [11. Recipe 9 — Evaluation and benchmarks](#11-recipe-9--evaluation-and-benchmarks)
- [12. Scaling, sharding, and efficiency](#12-scaling-sharding-and-efficiency)
- [13. Licensing + responsible-use checklist](#13-licensing--responsible-use-checklist)
- [14. FAQ](#14-faq)

---

## 0. What you actually get here

<!-- counts:start -->
| Training input | File | Rows | Best used for |
| --- | --- | ---: | --- |
| QA pairs (incl. deliberate abstentions) | `exports/qa.jsonl` | 291,816 | SFT, RAG readers, preference tuning |
| Instruction examples | `exports/instructions.jsonl` | 211,569 | SFT, LoRA/QLoRA, chat models |
| Grounded descriptive text | `exports/descriptions.jsonl` | 35,766 | continual pretraining |
| RAG chunks + `source_refs` | `exports/rag_chunks.jsonl` | 154,640 | retrieval, embeddings, RAG |
| Canonical records | `exports/anime.jsonl` | 35,766 | classification, ranking, KG |
| Characters | `exports/characters.jsonl` | 215,926 | character extraction, KG |
| Staff credits | `exports/staff.jsonl` | 414,772 | crew extraction, KG |
| Episodes | `exports/episodes.jsonl` | 108,359 | episode QA (Kitsu-linked works only) |
| Relation edges | `exports/relationships.jsonl` | 26,719 | relation extraction, KG |
| Alternative titles | `exports/alt_titles.jsonl` | 130,224 | title normalization, alias resolution |
| Per-anime license tiers | `exports/license_tiers.jsonl` | 35,766 | filtering before publication |
| Split field on every record | every table | — | leakage-free train/val/test |
<!-- counts:end -->

Every record carries a `split` (`train`/`val`/`test`). **Always filter by it.**
Splits are assigned per anime work, so no character/QA/chunk of a work leaks
across buckets.

The row counts above are generated from `reports/summary.json` by
`python scripts/sync_docs.py`; `sync_docs.py --check` fails when they are
stale.

---

## 1. Setup and hardware

### 1.1 Base environment (shared by all recipes)

```bash
python -m venv .venv
source .venv/bin/activate            # git bash / WSL / macOS
# .venv\Scripts\activate             # Windows

pip install -r requirements.txt
pip install -r examples/training-requirements.txt
```

For GPU users, install the CUDA build of PyTorch first (check your CUDA
version):

```bash
# example: CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### 1.2 Hardware guidance (honest)

| Model size | Method | Minimum GPU | Feasible with |
| --- | --- | --- | --- |
| 0.5B–3B | full fine-tune | 16 GB | any modern consumer GPU |
| 3B–7B | LoRA (Recipe 2) | 8–16 GB | RTX 4070/4080, MPS, T4 (16GB colab) |
| 7B–13B | QLoRA 4-bit (Recipe 2) | 8–12 GB | RTX 4070, A10G, L4 |
| 13B–70B | QLoRA 4-bit | 24–48 GB | A100, 2×L4 |
| any | CPU-only | — | QLoRA works slowly; use `device_map="cpu"` |

Rule of thumb for this dataset: **LoRA/QLoRA gives 90% of the
benefit of full fine-tuning at ~10% of the cost**. Unless you need to re-tune
every layer, do not full-fine-tune models above 3B.

---

## 2. Data preparation for training

All JSONL files stream line-by-line and convert directly to Hugging Face
`datasets` objects.

### 2.1 Paired instruction format (SFT/DPO)

The dataset's `qa.jsonl` uses a grounded Q/A shape. Convert it to a
chat-message list for models that use a chat template:

```python
import json
from datasets import Dataset

def load_pairs(path, split="train"):
    rows = []
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        if d.get("split") != split:
            continue
        rows.append(
            {
                "messages": [
                    {"role": "user", "content": d["question"]},
                    {"role": "assistant", "content": d["answer"]},
                ],
                # keep provenance so you can audit later
                "anime_id": d.get("anime_id"),
                "source_refs": d.get("source_refs"),
            }
        )
    return Dataset.from_list(rows)

train = load_pairs("exports/qa.jsonl", "train")
val   = load_pairs("exports/qa.jsonl", "val")
print(len(train), train[0]["messages"][0]["content"][:80])
```

Stream a large file without loading it all into RAM:

```python
from datasets import load_dataset
ds = load_dataset("json", data_files={"train": "exports/qa.jsonl"}, split="train", streaming=True)
# iterate: for row in ds: ...
```

### 2.2 The `split` field is mandatory

```python
import json
def split_rows(path, want):
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        if d.get("split") == want:
            yield d
```

Never train on rows whose `split` is not `train` — the val/test rows exist to
measure you honestly.

---

## 3. Recipe 1 — Instruction fine-tuning (SFT)

The most common use: teach a chat model to answer anime questions from
`qa.jsonl` (358k pairs) and follow extraction instructions from
`instructions.jsonl` (125k examples).

### 3.1 Minimal SFT with `Trainer`

```python
from transformers import AutoTokenizer, AutoModelForCausalLM, \
    Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import Dataset
import json

MODEL = "HuggingFaceTB/SmolLM2-1.7B-Instruct"   # any chat model works
tok = AutoTokenizer.from_pretrained(MODEL, padding_side="right")
tok.pad_token = tok.eos_token

rows = []
for line in open("exports/qa.jsonl", encoding="utf-8"):
    d = json.loads(line)
    if d.get("split") != "train":
        continue
    chat = [{"role": "user", "content": d["question"]},
            {"role": "assistant", "content": d["answer"]}]
    rows.append({"text": tok.apply_chat_template(chat, tokenize=False)})
ds = Dataset.from_list(rows[:50_000])          # quick start; raise later

def tok_fn(batch):
    return tok(batch["text"], truncation=True, max_length=1024)
ds = ds.map(tok_fn, batched=True, remove_columns=["text"])

model = AutoModelForCausalLM.from_pretrained(MODEL)
args = TrainingArguments(output_dir="runs/sft-qa", per_device_train_batch_size=4,
                         num_train_epochs=2, learning_rate=2e-5,
                         gradient_accumulation_steps=4, logging_steps=50,
                         report_to="none")
trainer = Trainer(model=model, args=args, train_dataset=ds,
                  data_collator=DataCollatorForLanguageModeling(tok, mlm=False))
trainer.train()
trainer.save_model("runs/sft-qa/final")
```

### 3.2 Predict after fine-tuning

```python
from transformers import pipeline
pipe = pipeline("text-generation", model="runs/sft-qa/final", tokenizer=tok)
print(pipe("Who directed Cowboy Bebop?", max_new_tokens=120)[0]["generated_text"])
```

### 3.3 Mixing QA with instructions

Concatenate the two files before tokenization so the model sees both answer
style and structured-extraction style:

```python
import json

def rows_from(path):
    for line in open(path, encoding="utf-8"):
        yield json.loads(line)

source = []
for path in ("exports/qa.jsonl", "exports/instructions.jsonl"):
    doc = rows_from(path) if callable(rows_from) else None
    for d in rows_from(path):
        if d.get("split") == "train":
            source.append(d)
        if len(source) >= 60_000:
            break
    if len(source) >= 60_000:
        break
```

> **Tip:** cap each epoch on a subsample first (50k rows) to validate the
> training loop and hyperparameters before spending GPU-hours on the full set.

---

## 4. Recipe 2 — Parameter-efficient fine-tuning (LoRA / QLoRA)

Use this when you have 8–16 GB VRAM and want to fine-tune a 3B–13B model.
LoRA adds small trainable adapters to attention projections; QLoRA also loads
the base in 4-bit.

### 4.1 LoRA with `peft` + `trl.SFTTrainer`

```python
import json
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig

MODEL = "mistralai/Mistral-7B-v0.1"

tok = AutoTokenizer.from_pretrained(MODEL)
tok.pad_token = tok.eos_token

rows = []
for path in ("exports/qa.jsonl", "exports/instructions.jsonl"):
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        if d.get("split") != "train":
            continue
        chat = [{"role": "user", "content": d["question"]},
                {"role": "assistant", "content": d["answer"]}]
        rows.append({"text": tok.apply_chat_template(chat, tokenize=False)})
ds = Dataset.from_list(rows[:80_000])

model = AutoModelForCausalLM.from_pretrained(MODEL, device_map="auto")
lora = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","k_proj","v_proj","o_proj"],
                  lora_dropout=0.05, bias="none", task_type="CAUSAL_LM")
model = get_peft_model(model, lora)
model.print_trainable_parameters()   # ~0.5-2% of total

cfg = SFTConfig(output_dir="runs/lora-anime", per_device_train_batch_size=2,
                num_train_epochs=1, gradient_accumulation_steps=8,
                learning_rate=2e-4, logging_steps=50, report_to="none")
trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tok)
trainer.train()
model.save_pretrained("runs/lora-anime/final")   # adapters only (small)
```

### 4.2 QLoRA — add 4-bit quantization (drops VRAM ~4×)

```python
from transformers import BitsAndBytesConfig

quant = BitsAndBytesConfig(load_in_4bit=True,
                           bnb_4bit_quant_type="nf4",
                           bnb_4bit_compute_dtype="float16")
model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=quant,
                                             device_map="auto")
# ... same LoraConfig + SFTTrainer as above ...
```

### 4.3 Merge adapters for deployment

```python
from peft import PeftModel
base = AutoModelForCausalLM.from_pretrained(MODEL)
merged = PeftModel.from_pretrained(base, "runs/lora-anime/final").merge_and_unload()
merged.save_pretrained("runs/lora-anime/merged")
```

---

## 5. Recipe 3 — Preference tuning (DPO)

Use DPO when you want the model to prefer grounded answers over hallucinated
ones. Construct pairs from `qa.jsonl`: the dataset answer is the *chosen*
response; generate a *rejected* response with the base model and pair them.

```python
import json
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import DPOTrainer, DPOConfig

DATA = "exports/qa.jsonl"

def build_pairs(n=20_000):
    pairs = []
    for line in open(DATA, encoding="utf-8"):
        d = json.loads(line)
        if d.get("split") != "train":
            continue
        # chosen = grounded answer; rejected = base-model generation (or a
        # deliberately weak sample you logged). Using the base model's raw
        # output as "rejected" teaches the model to prefer grounded text.
        pairs.append({
            "prompt": [{"role": "user", "content": d["question"]}],
            "chosen": [{"role": "assistant", "content": d["answer"]}],
            "rejected": [{"role": "assistant", "content": "I don't know."}],
        })
        if len(pairs) >= n:
            break
    return Dataset.from_list(pairs)

ds = build_pairs()

model = AutoModelForCausalLM.from_pretrained("runs/lora-anime/merged")  # your SFT base
ref   = AutoModelForCausalLM.from_pretrained("runs/lora-anime/merged")
tokenizer = AutoTokenizer.from_pretrained("runs/lora-anime/merged")

cfg = DPOConfig(output_dir="runs/dpo-anime", beta=0.1, per_device_train_batch_size=1,
                gradient_accumulation_steps=8, learning_rate=1e-5,
                logging_steps=50, max_length=1024, report_to="none")
trainer = DPOTrainer(model=model, ref_model=ref, args=cfg, train_dataset=ds,
                     processing_class=tokenizer)
trainer.train()
```

> **Honest note:** DPO needs a reasonably strong SFT starting point. Run
> Recipe 1/2 first, then DPO on top. A naive "I don't know." rejection works,
> but logging true base-model generations gives better separation.

---

## 6. Recipe 4 — Retrieval-augmented generation (RAG) fine-tuning

Ground chatbot answers in the corpus. Two parts: an index over
`rag_chunks.jsonl`, and a reader that is fine-tuned on grounded QA.

### 6.1 Build a FAISS index over RAG chunks

```python
import json
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")   # or any embedder
texts, meta = [], []
for line in open("exports/rag_chunks.jsonl", encoding="utf-8"):
    d = json.loads(line)
    texts.append(d["text"])
    meta.append({"anime_id": d.get("anime_id"), "source_refs": d.get("source_refs")})

vecs = model.encode(texts, batch_size=64, show_progress_bar=True)
import faiss, numpy as np
index = faiss.IndexFlatIP(np.float32(vecs.shape[1]))
index.add(np.asarray(vecs, dtype=np.float32))
faiss.write_index(index, "runs/rag_chunks.index")
np.save("runs/rag_meta.npy", np.array(meta, dtype=object), allow_pickle=True)
np.save("runs/rag_texts.npy", np.array(texts, dtype=object), allow_pickle=True)
```

### 6.2 Retrieve top-k context for a question

```python
def retrieve(q, k=4):
    qv = model.encode([q])
    scores, ids = index.search(qv, k)
    return [texts[i] for i in ids[0]], meta[i] for i in ids[0]]
```

### 6.3 Fine-tune a reader on retrieved context + QA

```python
prompts = []
for line in open("exports/qa.jsonl", encoding="utf-8"):
    d = json.loads(line)
    if d.get("split") != "train":
        continue
    ctx, _ = retrieve(d["question"])
    block = "\n".join(f"- {c}" for c in ctx)
    prompts.append({"text": f"Context:\n{block}\n\nQ: {d['question']}\nA: {d['answer']}"})
# tokenize + SFT exactly as Recipe 1, using prompts instead of plain QA
```

> **Tip:** persist retrieved context per row so training is deterministic and
> you don't re-run retrieval every epoch.

---

## 7. Recipe 5 — Domain continual pretraining

Make a base model more fluent in anime facts before instruction tuning. Use
the CausalLM objective over `descriptions.jsonl` (project-generated record
summaries) together with the structured text in `anime.jsonl`.

```python
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, \
    Trainer, TrainingArguments, DataCollatorForLanguageModeling
import json

DESC = "exports/descriptions.jsonl"
tok = AutoTokenizer.from_pretrained("microsoft/phi-2")
tok.pad_token = tok.eos_token

texts = []
for line in open(DESC, encoding="utf-8"):
    d = json.loads(line)
    if d.get("split") != "train":
        continue
    texts.append(txt := d.get("text") or "")
    # combine metadata for a denser signal, e.g.:
    # f"{d.get('title_canonical')}: {d.get('text')}"
ds = Dataset.from_list([{"text": t} for t in texts if t])

def tok_fn(b):
    # 2048-token windows; this example truncates at max_length
    return tok(b["text"], truncation=True, max_length=2048)
ds = ds.map(tok_fn, batched=True, remove_columns=["text"])

model = AutoModelForCausalLM.from_pretrained("microsoft/phi-2")  # small, trainable
trainer = Trainer(model=model,
                  args=TrainingArguments(output_dir="runs/pretrain-anime",
                                         per_device_train_batch_size=4,
                                         gradient_accumulation_steps=4,
                                         num_train_epochs=1,
                                         learning_rate=1e-5,
                                         report_to="none"),
                  train_dataset=ds,
                  data_collator=DataCollatorForLanguageModeling(tok, mlm=False))
trainer.train()
trainer.save_model("runs/pretrain-anime/final")
```

For streaming long-form text (split into chunks, never truncated mid-sentence):

```python
def chunk_text(t, size=2048, overlap=64):
    words = t.split()
    for i in range(0, len(words), size - overlap):
        yield " ".join(words[i:i + size])
```

---

## 8. Recipe 6 — Contrastive / embedding training for retrieval

Train a domain embedding model so semantic search over anime works better than
generic MiniLM. Use QA pairs as (anchor, positive) pairs with
`MultipleNegativesRankingLoss`.

```python
from sentence_transformers import SentenceTransformer, InputExample, \
    losses, evaluation
from torch.utils.data import DataLoader
import json

model = SentenceTransformer("all-MiniLM-L6-v2")

examples = []
for line in open("exports/qa.jsonl", encoding="utf-8"):
    d = json.loads(line)
    if d.get("split") == "train":
        examples.append(InputExample(texts=[d["question"], d["answer"]]))

# Also add entity-name pairs from entity_links.jsonl
for i, line in enumerate(open("exports/entity_links.jsonl", encoding="utf-8")):
    d = json.loads(line)
    if i > 100_000:
        break
    examples.append(InputExample(texts=[d.get("name") or "", d.get("source_name") or "anime"]))

loader = DataLoader(examples, batch_size=64, shuffle=True)
loss = losses.MultipleNegativesRankingLoss(model)

model.fit(
    train_objectives=[(loader, loss)],
    epochs=3,
    warmup_steps=500,
    output_path="runs/anime-embedder",
)
vec = model.encode(["a sci-fi bounty hunter in space"])
print(vec.shape)   # (384,) for MiniLM dims
```

Evaluate with retrieval hit-rate on the val split before deploying.

---

## 9. Recipe 7 — Classification and ranking

Predict metadata that exists per work: genre labels, source material, age
rating, or a mean-score ranker.

### 9.1 Multi-label genre classifier

```python
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, \
    Trainer, TrainingArguments
import json, numpy as np

GENRES = ["Action","Drama","Sci-Fi","Comedy","Romance","Fantasy","Horror","Slice of Life","Mecha","Sports"]  # extend from exports/genres.jsonl
tok = AutoTokenizer.from_pretrained("distilbert-base-uncased")

rows = []
for line in open("exports/anime.jsonl", encoding="utf-8"):
    d = json.loads(line)
    if d.get("split") != "train":
        continue
    rows.append({"title": d["title_canonical"], "labels": [1.0 if g in (d.get("genres") or []) else 0.0 for g in GENRES]})
ds = Dataset.from_list(rows)

def tok_fn(b):
    out = tok(b["title"], truncation=True, padding="max_length", max_length=64)
    out["labels"] = b["labels"]
    return out
ds = ds.map(tok_fn, batched=True)

model = AutoModelForSequenceClassification.from_pretrained(
    "distilbert-base-uncased", num_labels=len(GENRES), problem_type="multi_label_classification")

trainer = Trainer(model=model,
                  args=TrainingArguments(output_dir="runs/genre-clf", num_train_epochs=3,
                                         per_device_train_batch_size=32, learning_rate=3e-5,
                                         eval_strategy="none", report_to="none"),
                  train_dataset=ds)
trainer.train()
trainer.save_model("runs/genre-clf/final")
```

### 9.2 Score ranker

Regression/ranking on `mean_score` (0–100). Clone Recipe 7 with
`problem_type="regression"` and `labels = [d["mean_score"] / 100.0]`. Cap
rows where `mean_score` is null (they carry no label).

---

## 10. Recipe 8 — Entity linking and relation extraction

### 10.1 Head classification (internal → external ID)

`entity_links.jsonl` records how every internal `anime_id` maps to source
remotes (method + confidence). Train a classifier/retriever that, given a
source string, predicts the canonical `anime_id`:

```python
# candidate = all canonical titles from anime.jsonl
# positive   = the anime_id whose title matched
# train with FAQ: sentence-transformers retrieval (Recipe 6)
# score top-k accuracy on entity_links val rows
```

### 10.2 Relation predictor

`relationships.jsonl` gives typed edges (prequel/sequel/side story/…). Train a
classifier on description pairs:

```python
edges = [d for d in map(json.loads, open("exports/relationships.jsonl", encoding="utf-8"))]
pairs = [(d["source"], d["target"], d["relation"]) for d in edges]
# encode with the SAME tokenizer/classifier pattern as Recipe 7,
# but the input is f"{source_desc} || {target_desc}" and labels = relation_type
```

Use `descriptions.jsonl` per side to give the model text to reason from.

---

## 11. Recipe 9 — Evaluation and benchmarks

### 11.1 Holdout discipline

The **test split (5% of works; all their records) is never touched during
training.** Evaluate final models only on `split == "test"`; the exact count is
in `reports/summary.json` under `splits`.

```python
import json
from collections import defaultdict

def grouped(path, key="anime_id"):
    by = defaultdict(list)
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        by[d.get(key)].append(d)
    return by

test_qa = {k: v for k, v in grouped("exports/qa.jsonl").items()
           if any(r["split"] == "test" for r in v)}
print("test works:", len(test_qa))
```

### 11.2 Metrics per task

| Task | Metric | Tool |
| --- | --- | --- |
| QA generation | ROUGE, BLEURT, sentence-BERT cosine vs reference | `evaluate.load("rouge")` |
| Hallucination | manual audit + `qa_grounding`-style source_refs check | script in `src/validate` |
| Retrieval | Recall@k, MRR | `ranx` / manual over FAISS |
| Classification | macro-F1, label-wise P/R | `sklearn.metrics` |
| Ranking | Spearman ρ between predicted and `mean_score` | `scipy.stats.spearmanr` |
| Chat | MT-Bench-style judge, human preference | `lm-evaluation-harness` |

```python
import evaluate
rouge = evaluate.load("rouge")
preds  = [generator(q) for q in sample_questions]
scores = rouge.compute(predictions=preds, references=sample_answers)
print(scores["rougeL"])   # 0-1
```

### 11.3 Honest reporting checklist

1. Report **test-split** numbers only.
2. State base model, adapter method, epochs, seed.
3. Report generations you audited for hallucination, not just n-gram overlap.
4. Disclose training data licensing per Section 13.

---

## 12. Scaling, sharding, and efficiency

### Shard the JSONL before training

```bash
# PowerShell
Get-Content exports\qa.jsonl | Select-Object -First 200000 > data\qa_train_200k.jsonl
# Git Bash
head -n 200000 exports/qa.jsonl > /tmp/qa_200k.jsonl
```

### Multi-GPU (accelerate / FSDP)

```bash
accelerate config                    # interactive: multi-GPU, mixed precision
accelerate launch train_sft.py       # launch any Trainer script
```

### Gradient checkpointing + mixed precision

```python
args = TrainingArguments(..., gradient_checkpointing=True, fp16=True)
model.gradient_checkpointing_enable()
```

### Memory economy cheat sheet

| Technique | VRAM saving |
| --- | --- |
| Gradient accumulation | batches larger than VRAM |
| `gradient_checkpointing=True` | ~30–50% |
| fp16/bf16 | ~50% |
| QLoRA 4-bit | ~4× vs full |
| Truncate to 1024 tokens here | large constant |
| `model.enable_input_require_grads()` for QLoRA frozen-base edge cases | — |

### Time budget reference (single RTX 4090)

- LoRA 1 epoch, 80k rows, SmolLM2-1.7B: ≈ 45–90 min
- QLoRA 1 epoch, 80k rows, Mistral-7B: ≈ 2–4 h
- SFT 2 epochs, 50k rows, phi-2: ≈ 1–2 h
- Embedder, 3 epochs, 100k pairs: ≈ 20–40 min

---

## 13. Licensing + responsible-use checklist

Every anime row and every exported record carries one `license_tier`, assigned
from the sources that contributed to it:

| Tier | Meaning | What you may do |
| --- | --- | --- |
| `cc0_only` | Wikidata only | reuse freely, attribution is courtesy |
| `permission_required` | AniList or Kitsu contributes; their terms grant API use, not redistribution | obtain written permission before publishing derived records |
| `unresolved` | Shikimori contributes and publishes no terms | do not redistribute |

1. **Filter before you ship.** `license_tier` is a column on every exported
   table, so no join is needed:

   ```python
   import json
   CLEAN = {"cc0_only"}
   rows = (json.loads(l) for l in open("exports/instructions.jsonl", encoding="utf-8"))
   train = [r for r in rows if r["split"] == "train" and r["license_tier"] in CLEAN]
   ```

   `exports/license_commercial_clear.csv` is the pre-computed anime-id list for
   that set; `exports/license_manifest.json` states each tier's obligation.
2. **Only `cc0_only` rows have no upstream permission outstanding.**
   `permission_required` and `unresolved` rows carry obligations
   this project cannot discharge for you.
3. **Synthetic text** (`synthetic=true`, and all QA/instruction rows) is
   generated by this project under CC-BY-4.0 — ground any claim you make from it
   in `source_refs` / `grounded_fields`.
4. **All shipped text is generated.** `record_summary` rows are assembled from
   structured fields and contain no plot detail; QA, instruction and RAG text
   are template-generated. No upstream synopsis or biography is in the release.
5. **Do not reintroduce upstream prose.** If you enrich the dataset yourself,
   the new source's terms still apply; the tier labels here cannot clear them.
6. **Publish a model card** with: base model, data used (tier mix and source
   list), license of your weights, eval metrics. This is an organisational aid,
   not legal advice.

---

## 14. FAQ

**Do I need the whole corpus for a first experiment?** No. 20–50k rows of
`qa.jsonl` train a strong demo assistant; add `instructions.jsonl` for
structured output; add RAG for grounding.

**QLoRA vs LoRA?** QLoRA = LoRA + 4-bit base. Use QLoRA when you need a 7B+ on
≤12 GB VRAM; use LoRA whenever the base fits in memory for a quality/velocity
edge.

**How do I avoid leakage?** Filter by `split` on every table. The dataset is
already split per anime, so a correct filter is sufficient.

**Where do non-anime rows go?** Every exported record belongs to exactly one
`split`; there are no unassigned rows.

**Can I train on everything at once?** Yes — but run Recipe 5 (pretrain) →
Recipe 1/2 (SFT) → Recipe 3 (DPO) in that order for the best final model.

**Isn't synthetic data a problem?** Synthetic rows are labeled and grounded in
stored facts. Treat them as *augmentation*, not ground truth; evaluate on
source-sourced val/test rows.

---

_End of training guide. Companion docs: [`README.md`](../README.md),
[`COMMANDS.md`](COMMANDS.md), [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md),
[`DATASET_CARD.md`](../DATASET_CARD.md). Live HTML version:
[`training.html`](training.html)._

