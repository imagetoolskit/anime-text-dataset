# Commands, Terms, and Terminals — Complete Reference

> Every command in this document runs from **Windows CMD**, **PowerShell 5/7**,
> and **Git Bash / WSL / macOS** unless stated otherwise. Where a command
> differs per shell, each variant is shown. Replace `python` with `python3`
> where your environment only exposes `python3`.

This is the terminal companion to the
[Large Anime Text Dataset](../README.md): setup, ways to access the data, the
pipeline driver (`src.cli`), data exploration, verification, model-training
entry points, and troubleshooting.

---

## Table of contents

- [1. Prerequisites](#1-prerequisites)
- [2. Ways to access, clone, or train](#2-ways-to-access-clone-or-train)
- [3. Setting up the environment](#3-setting-up-the-environment)
- [4. Repository layout](#4-repository-layout)
- [5. The pipeline driver (`python -m src.cli`)](#5-the-pipeline-driver-python--m-srcccli)
- [6. Per-phase command reference](#6-per-phase-command-reference)
- [7. Configuration and environment variables](#7-configuration-and-environment-variables)
- [8. Exploring the exported dataset](#8-exploring-the-exported-dataset)
- [9. Verifying data and checksums](#9-verifying-data-and-checksums)
- [10. Dataset tooling: profile, license tiers, doc sync, Hub publish](#10-dataset-tooling-profile-license-tiers-doc-sync-hub-publish)
- [11. Model-training entry points](#11-model-training-entry-points)
- [12. Resuming and troubleshooting](#12-resuming-and-troubleshooting)
- [13. Command cheat sheet](#13-command-cheat-sheet)

---

## 1. Prerequisites

| Tool | Minimum | Purpose | Check |
| --- | --- | --- | --- |
| Python | 3.12+ | pipeline, exports, training code | `python --version` |
| Git | 2.x | version control | `git --version` |
| pip | any | Python dependencies | `python -m pip --version` |
| SQLite (optional) | 3.x | direct DB exploration | `sqlite3 --version` |
| DuckDB (optional) | 1.x | fast analytics on Parquet | `duckdb --version` |
| jq (optional, Git Bash/WSL) | any | JSONL streaming | `jq --version` |

No API keys are required to re-run the pipeline: every reachable source is a
public endpoint. Secrets (only `HF_TOKEN` for publishing) go in the environment
or `config/.env` — never commit them.

---

## 2. Ways to access, clone, or train

Eight gateways into the same data. Pick the one that matches what you build.

| # | Method | What you get | How |
| --- | --- | --- | --- |
| 1 | **Clone the repository** | code, schemas, docs, pipeline | `git clone https://github.com/muqeet-1138/anime-text-dataset.git` |
| 2 | **Download the full data** | the full `exports/` tree (JSONL, SQLite, Parquet, CSV) | request access to the gated [Hugging Face dataset](https://huggingface.co/datasets/muqeet-1138/anime-text-dataset) |
| 3 | **Stream JSONL in Python** | train-ready rows without loading everything | line loop over `exports/*.jsonl` |
| 4 | **Hugging Face `datasets` loader** | a sharded, streamable HF `Dataset` | `load_dataset("muqeet-1138/anime-text-dataset", "qa")` |
| 5 | **SQLite database** | joins and referential queries | `sqlite3` CLI or Python stdlib |
| 6 | **Parquet + DuckDB / pandas** | fast analytics | `duckdb -c "..."` or `pd.read_parquet` |
| 7 | **CSV** | spreadsheet-friendly flat view | open `exports/anime.csv` |
| 8 | **Training recipes** | fine-tuned models | `docs/TRAINING.md` + `examples/` scripts |

Runnable examples for every row of this table are in
[Section 8](#8-exploring-the-exported-dataset) (exploration) and
[Section 11](#11-model-training-entry-points) (training).

---

## 3. Setting up the environment

Python virtual environment (recommended):

```bash
# create
python -m venv .venv

# activate — Windows CMD
.venv\Scripts\activate.bat
# activate — Windows PowerShell
.venv\Scripts\Activate.ps1
# activate — Git Bash / WSL / macOS
source .venv/bin/activate

# install base deps
pip install -r requirements.txt
```

Optional tooling for the fast-analytics paths in Section 8:

```bash
pip install duckdb           # Parquet analytics
# Git Bash / WSL: sudo apt install sqlite3 jq   (Debian/Ubuntu)
```

---

## 4. Repository layout

```
.
├── config/                 # settings + env template
├── docs/                   # rendered site + reference docs (markdown)
│   ├── index.html          #   site home (generated from docs_src/)
│   ├── commands.html       #   this guide as a web page (generated)
│   ├── training.html       #   training-methods web page (generated)
│   ├── explore.html        #   data explorer (reads docs/data/profile.json)
│   ├── COMMANDS.md         #   this file
│   ├── TRAINING.md         #   the full training guide
│   ├── DATA_DICTIONARY.md  #   field-level reference
│   ├── SCHEMAS.md          #   schema notes
│   └── LICENSE_NOTES.md    #   licensing and tiers
├── docs_src/               # editable HTML source with {{n:…}} count tokens
├── examples/               # runnable training scripts
├── exports/                # generated dataset (Hugging Face, git-ignored)
├── logs/                   # run logs
├── reports/                # final report + summary.json
├── scripts/                # data_profile, license_tiers, sync_docs, upload_hf
├── src/
│   ├── cli.py              # pipeline driver (see Section 5)
│   ├── pipeline/           # discover … export
│   ├── sources/            # AniList, Kitsu, Shikimori, Wikidata, ANN clients
│   └── validate/           # validators.py, report.py
├── tests/                  # pytest suite (unit + end-to-end fixture)
├── CITATION.cff
├── DATASET_CARD.md
├── LICENSE
├── README.md
└── requirements.txt
```

---

## 5. The pipeline driver (`python -m src.cli`)

The whole build is driven by one module. Running it with no arguments prints
the command list:

```bash
python -m src.cli
# commands: discover | dedup | backfill | refill | enrich | entities |
#           normalize | relationships | descriptions | qa | instructions |
#           franchise | rag | validate | split | export | checksums | report
```

Every phase:

- **Writes to SQLite** (`data/anime.db`, WAL mode) — resumable via checkpoints.
- **Holds an HTTP cache** of raw payloads — re-runs are cheap.
- Is **idempotent**: each output table is rebuilt from upstream tables, so you
  can re-run any phase at any time.

Three phases are **scripts rather than subcommands**, because they operate on
the exported files: `scripts/license_tiers.py`, `scripts/sync_docs.py` and
`scripts/data_profile.py` (pass `--out docs/data/profile.json` for the copy the
site loads).

---

## 6. Per-phase command reference

**Order matters.** The canonical build order is:

```
discover → dedup → backfill → refill → enrich → entities → normalize →
relationships → franchise → descriptions → qa → instructions → rag → split →
license_tiers → export → validate → checksums → report → sync_docs → data_profile
```

`license_tiers` runs **before** `export` so every exported row carries a real
`license_tier` instead of a null column. `validate` reads the exported files, so
it runs **after** `export`. `sync_docs` reads `reports/summary.json`, so it runs
**after** `report`.

### Phase 0 — Discovery

```bash
# one source at a time
python -m src.cli discover anilist
python -m src.cli discover kitsu
python -m src.cli discover shikimori
python -m src.cli discover wikidata
python -m src.cli discover ann

# default: discover all reachable sources
python -m src.cli discover
```

### Phase 1 — Entity resolution

```bash
python -m src.cli dedup       # raw source rows → canonical anime works
python -m src.cli backfill    # fill missing fields from stored payloads
python -m src.cli refill      # re-fetch stale or failed payloads
```

To force a clean re-run of any checkpointed phase:

```bash
python -c "import sys; sys.path.insert(0,'.'); from src.db import connect; c=connect(); c.execute(\"delete from checkpoint where key='dedup_done'\"); c.commit()"
python -m src.cli dedup
```

### Phase 2 — Enrichment (depth tier)

```bash
# default: enrich the top ~20% works by mean score
python -m src.cli enrich anilist
python -m src.cli enrich shikimori
python -m src.cli enrich roles
python -m src.cli enrich related
python -m src.cli enrich episodes

# extend detail to EVERY linked work (slow: ~5–6 h at the configured rate)
python -m src.cli enrich anilist --all
python -m src.cli enrich shikimori --all
python -m src.cli enrich roles --all
python -m src.cli enrich related --all
python -m src.cli enrich episodes --all
```

`roles` and `related` only fetch works that already have a Shikimori `detail`
record, so run `enrich shikimori --all` first when you want cast/crew and
relations for the whole catalogue.

### Phase 3 — Entities and normalization

```bash
python -m src.cli entities     # characters, staff, studios, episodes
python -m src.cli normalize    # merges duplicates, canonicalizes enums,
                               # rescales scores, strips HTML, dedupes
                               # alt titles / characters / staff / relations
```

`normalize` is mandatory after `entities`: it is the stage that removes exact
duplicate works, repairs out-of-range values, moves Cyrillic Shikimori names
into `name_ru`, and collapses duplicate entity rows. Skipping it leaves the
duplicate-title validation failing.

### Phase 4–10 — Derived tables

```bash
python -m src.cli relationships   # anime-to-anime edges only
python -m src.cli franchise       # strong-relation franchise clusters
python -m src.cli descriptions    # record summaries + attributed upstream synopses
python -m src.cli qa              # grounded QA pairs (~30 question types)
python -m src.cli instructions    # instruction examples (12 task types)
python -m src.cli rag             # prose RAG chunks with kind + source_refs
python -m src.cli split           # 90/5/5 splits, per-anime, seed 42
```

### Phase 11 — Tier, export and verify

```bash
python scripts/license_tiers.py   # tiers in the DB, manifest, per-tier id subsets
python -m src.cli export          # JSONL + SQLite + Parquet + CSV
python -m src.cli validate        # 21 checks over the exported files
python -m src.cli checksums       # SHA-256 sidecars + checksums.json
python -m src.cli report          # reports/final_report.md + summary.json
python scripts/sync_docs.py       # refresh generated tables in the docs
```

`license_tiers` runs before `export` so the tier is joined into every exported
row; `checksums` runs after everything that writes into `exports/`.
`scripts/sync_docs.py --check` exits non-zero when a doc table is stale, which
is the hook to use in CI.

---

## 7. Configuration and environment variables

Two layers: `config/config.json` (committed defaults) and environment variables
(override at runtime). Copy the template to start:

```bash
copy config\.env.example config\.env       # Windows CMD
cp  config/.env.example  config/.env       # Git Bash / WSL / macOS
```

| Variable | Meaning | Default |
| --- | --- | --- |
| `MAX_RUNTIME_HOURS` | global wall-clock budget | from config |
| `SRC_PER_SECOND` | per-source request throttle | from config |
| `SRC_CHECKPOINT_EVERY` | rows between progress checkpoints | from config |
| `SRC_SEED` | RNG seed (splits etc.) | 42 |
| `HF_TOKEN` | Hugging Face write token, only for `upload_hf.py` | unset |

`config/config.json` also holds the per-source budgets
(`max_source_runtime_hours`), the rate limits, and `enrichment_tier`
(`{"all": true}` switches enrichment from the top-20% tier to every work).

---

## 8. Exploring the exported dataset

### JSONL (universal)

```bash
# PowerShell — count rows
(Get-Content exports\anime.jsonl | Measure-Object -Line).Lines

# Git Bash / WSL / macOS
wc -l exports/anime.jsonl

# stream one record (PowerShell)
Get-Content exports\anime.jsonl -TotalCount 1

# grep for a title (Git Bash / WSL / macOS)
grep -m 5 -i '"Cowboy Bebop"' exports/anime.jsonl
```

### JSONL via Python (zero extra deps)

```bash
python -c "import json; A=[json.loads(l) for l in open('exports/anime.jsonl',encoding='utf-8')]; print(len(A), sum(1 for a in A if a['year']==2020))"
```

### JSONL via Hugging Face `datasets`

```bash
python -c "from datasets import load_dataset; print(load_dataset('json', data_files={'train':'exports/qa.jsonl'}, split='train', streaming=True))"
```

### SQLite (Python stdlib — no install)

```bash
python -c "import sqlite3; con=sqlite3.connect('exports/anime_dataset.sqlite'); [print(r) for r in con.execute('select year,count(*) from anime group by year order by 2 desc limit 5')]"
```

### SQLite (sqlite3 CLI)

```bash
sqlite3 exports/anime_dataset.sqlite "select title_canonical,year from anime where mean_score>80 order by year desc limit 10;"
```

### Parquet (DuckDB — fast, SQL)

```bash
duckdb -c "select year, count(*) n, cast(avg(mean_score) as int) avg_score from read_parquet('exports/anime.parquet') group by year order by year desc limit 10;"
```

### Parquet (pandas)

```bash
python -c "import pandas as pd; df=pd.read_parquet('exports/anime.parquet'); print(df.groupby('year').size().tail())"
```

### QA pair sample

```bash
python -c "import json; qa=[json.loads(l) for l in open('exports/qa.jsonl',encoding='utf-8')]; print(json.dumps(qa[0], ensure_ascii=False, indent=2))"
```

### Filter by license tier before training

Every exported row carries `license_tier`, so no join is needed:

```bash
python -c "import json; rows=[json.loads(l) for l in open('exports/qa.jsonl',encoding='utf-8')]; clean=[r for r in rows if r['license_tier']=='cc0_only']; print(len(rows), '->', len(clean))"
```

---

## 9. Verifying data and checksums

Per-file SHA-256 (`.sha256` next to every export) and one manifest
`exports/checksums.json`. The manifest records `files_covered`, `algorithm`
and the files it deliberately excludes (itself and the `.sha256` sidecars), so
it can be verified without a self-reference loop.

### PowerShell

```powershell
$manifest = Get-Content exports\checksums.json -Raw | ConvertFrom-Json
foreach ($f in $manifest.files) {
  $h = (Get-FileHash "exports\$($f.file)" -Algorithm SHA256).Hash.ToLower()
  if ($h -eq $f.sha256) { "OK   $($f.file)" } else { "BAD  $($f.file)" }
}
```

### Git Bash / WSL / macOS

```bash
cd exports
sha256sum -c *.sha256
```

### Download the dataset from Hugging Face

```bash
huggingface-cli download muqeet-1138/anime-text-dataset \
  --repo-type dataset --local-dir exports     # gated: request access first
```

---

## 10. Dataset tooling: profile, license tiers, doc sync, Hub publish

Four "making-it-publishable" scripts ship in `scripts/`.

### Regenerate the statistical profile

```bash
python scripts/data_profile.py                                # reports/data_profile.json
python scripts/data_profile.py --out docs/data/profile.json   # feeds docs/explore.html
```

The explorer page (`docs/explore.html`) reads `docs/data/profile.json`.
Regenerate both whenever exports change.

### Regenerate the per-anime license tiers

```bash
python scripts/license_tiers.py
# writes exports/license_tiers.jsonl, exports/license_manifest.json,
#        exports/license_tier_<tier>.csv, exports/license_commercial_clear.csv
```

One row per anime: `{anime_id, title, tier, sources, reason}`. Precedence is
`unresolved` > `permission_required` > `cc0_only`; a work takes
the strictest tier among its contributing sources. The manifest states each
tier's obligation explicitly and disclaims legal clearance. See
`docs/LICENSE_NOTES.md`.

### Sync the generated doc tables

```bash
python scripts/sync_docs.py           # rewrite the <!-- counts:start/end --> blocks
python scripts/sync_docs.py --check   # exit 1 if a block is stale (CI hook)
```

The blocks are generated from `reports/summary.json`, which is generated from
the database. Editing them by hand is pointless — the next run overwrites them.

### Publish the release to Hugging Face Hub

Three dataset repos share one schema: the full mixed-rights release is gated with
manual approval, the free 30% preview is gated with automatic approval, and the
CC0-only subset is public.

```bash
# full release: verify, then upload to a gated repo
python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset --gated manual --dry-run
python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset --gated manual

# free 30% preview: stratified sample, automatic approval
python scripts/build_preview_subset.py
python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset-preview --source exports_preview --gated auto --dry-run
python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset-preview --source exports_preview --gated auto

# public CC0-only subset
python scripts/build_open_subset.py
python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset-open --source exports_open --dry-run
python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset-open --source exports_open

# refresh only the card and citation docs on an existing repo
python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset --card-only
```

`huggingface_hub` is needed only for the real upload:
`pip install "huggingface_hub[cli]"`. The script never prints the token. The
preview is free but not public-domain: it keeps every licence tier, and only 291
of its 10,729 works are `cc0_only`.

Contact for access or licensing questions: contact@animearray.site.

---

## 11. Model-training entry points

Two places hold training code:

1. [`docs/TRAINING.md`](TRAINING.md) — nine recipes with full code and hardware
   guidance.
2. `examples/` — runnable scripts:
   - `examples/finetune_lora.py` (SFT + LoRA/QLoRA)
   - `examples/training-requirements.txt` (training-only dependencies)

Quick example:

```bash
pip install -r examples/training-requirements.txt

python examples/finetune_lora.py \
  --model mistralai/Mistral-7B-v0.1 \
  --data exports/instructions.jsonl \
  --split train \
  --epochs 2 \
  --output ./runs/anime-lora
```

---

## 12. Resuming and troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `database is locked` | another phase is holding the writer | run phases **sequentially**, never parallel writes |
| Unexpected counts after a source change | stale derived tables | re-run from `dedup` in the order in Section 6 |
| Duplicate-title validation fails | `normalize` was skipped after `entities` | run `python -m src.cli normalize` |
| `no such column: kind` | database predates the RAG `kind` column | re-run `python -m src.cli rag` (it migrates the column) |
| `Unknown command: X` | wrong subcommand | `python -m src.cli` to list valid names |
| Memory spike reading JSONL | whole file in RAM | stream line-by-line (Section 8) |
| `UnicodeEncodeError` in Windows terminals | cp1252 console | `$env:PYTHONIOENCODING='utf-8'` (PowerShell) or `chcp 65001` (cmd) |
| Checksum mismatch | corrupted/partial file | re-download the release asset or re-run `export` → `license_tiers` → `checksums` |
| `sync_docs.py` says a doc is stale | counts changed since the last report | `python -m src.cli report && python scripts/sync_docs.py` |

---

## 13. Command cheat sheet

| Goal | Command |
| --- | --- |
| Print all pipeline commands | `python -m src.cli` |
| Rebuild every export | `python -m src.cli export` |
| Assign license tiers | `python scripts/license_tiers.py` |
| Run repository checks (21) | `python -m src.cli validate` |
| Verify integrity | `python -m src.cli checksums` |
| Regenerate report | `python -m src.cli report` |
| Sync doc count tables | `python scripts/sync_docs.py` |
| Count anime | `python -c "import json;print(sum(1 for _ in open('exports/anime.jsonl',encoding='utf-8')))"` |
| Normalize after entities | `python -m src.cli normalize` |
| Enrich everything (slow) | `python -m src.cli enrich anilist --all` |
| Download the free 30% preview | `hf download muqeet-1138/anime-text-dataset-preview --repo-type dataset --local-dir exports_preview` |
| Download the full release (after approval) | `hf download muqeet-1138/anime-text-dataset --repo-type dataset --local-dir exports` |
| Regenerate data profile | `python scripts/data_profile.py` |
| Dry-run HF publish | `python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset --gated manual --dry-run` |
| Fine-tune with LoRA | `python examples/finetune_lora.py --data exports/instructions.jsonl` |
| Run the test suite | `python -m pytest -q` |
