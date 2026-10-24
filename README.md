# Large Anime Text Dataset — LLM & RAG Ready

> **Text-only anime dataset** built for fine-tuning large language models (LLM), instruction tuning, retrieval-augmented generation (RAG), question answering (QA), entity linking, recommendation systems, and evaluation benchmarks. The headline unit is **unique anime works** — one work expands into many records: characters, staff, episodes, QA pairs, RAG chunks, and relationship edges.

![version](https://img.shields.io/badge/version-2.0.0-blue)
![rows](https://img.shields.io/badge/unique%20anime-35k%2B-success)
![formats](https://img.shields.io/badge/formats-JSONL%20%7C%20SQLite%20%7C%20Parquet%20%7C%20CSV-lightgrey)
![license](https://img.shields.io/badge/license-per--record%20tiers-orange)

**Developer & maintainer:** Muhammad Muqeet — [muqeet@animearray.site](mailto:muqeet@animearray.site) · [muqeet@anitroves.com](mailto:muqeet@anitroves.com)

---

## Table of contents

- [Headline numbers](#headline-numbers)
- [What this dataset contains](#what-this-dataset-contains)
- [Coverage and known limits](#coverage-and-known-limits)
- [Ways to access, clone, or train](#ways-to-access-clone-or-train)
- [Formats and download](#formats-and-download)
- [Explore the data](#explore-the-data)
- [Sources and licensing](#sources-and-licensing)
- [Data objects](#data-objects)
- [Train / validation / test splits](#train--validation--test-splits)
- [Quick start: run commands in terminals](#quick-start-run-commands-in-terminals)
- [Command-line reference](#command-line-reference)
- [Explore the data from the terminal](#explore-the-data-from-the-terminal)
- [How to train models on this dataset](#how-to-train-models-on-this-dataset)
- [Load the data in Python](#load-the-data-in-python)
- [Frequently asked questions](#frequently-asked-questions)
- [Citation](#citation)
- [License](#license)

---

## Headline numbers

<!-- counts:start -->
| Metric | Value |
| --- | --- |
| Unique anime works with at least one title | **35,766** |
| Characters | 215,926 |
| Staff credits | 414,772 |
| Episodes | 108,359 |
| Alternative titles | 130,224 |
| Relationship edges | 26,719 |
| Franchise clusters | 29,257 |
| Record summaries | 35,766 |
| Question/answer pairs | 291,816 |
| Instruction-tuning examples | 211,569 |
| RAG chunks | 154,640 |
| Split: train / val / test | 32,189 / 1,788 / 1,789 |

Coverage of the anime table (share of rows carrying a value):

| Field | Coverage |
| --- | ---: |
| Year | 95% |
| Episode count | 94% |
| Per-episode records | 18% |
| Studios | 62% |
| Genres | 74% |
| Characters | 38% |
| Voice actors | 33% |
| Staff credits | 53% |
| Relationships | 33% |
<!-- counts:end -->

Every export ships with SHA-256 checksums, and `python -m src.cli validate` runs
21 checks covering uniqueness, referential integrity, enum conformance, value
ranges, split hygiene, answer grounding, corpus diversity, license coverage and
export schema.

The tables above are generated from `reports/summary.json` by
`python scripts/sync_docs.py`; they are never edited by hand. The site pages
are written in `docs_src/` and rendered into `docs/` by the same script, which
keeps the `{{n:…}}` count tokens in the source so later runs can refresh them.

---

## What this dataset contains

A **structured, factual, text-only** corpus about anime: the works themselves, their casts, the people who made them, the studios, the genres and themes, the episode lists, the narrative relations between works — and, most importantly for NLP, **hundreds of thousands of grounded rows of natural language about anime**.

Each anime work includes:

- **Identity and titles** — canonical, English, Japanese, and up to dozens of alternative titles per work.
- **Discovery metadata** — format, status, episode count, duration, air dates, season bucket, year.
- **Text content** — a generated record summary built from the work's own structured fields. Upstream synopses are not included (see `LICENSE_AUDIT.md`).
- **Scores and popularity** — mean score normalised to a single 0–100 scale, popularity, favourites.
- **Taxonomy** — genre and theme labels, source material, age rating.
- **Cast and crew** — characters with roles and voice actors, staff with per-record credit roles.
- **Episodes** — per-episode numbers, titles, air dates and lengths.
- **Relations** — prequel/sequel/side-story/spin-off edges plus franchise clusters.
- **Training-ready text** — QA pairs, instruction examples and RAG chunks, each grounded in fields of the same record.
- **Provenance and a license tier on every record** — source, remote ID, link method, confidence, and one of four redistribution tiers.

### The four text collections

| Collection | Rows per anime | What it teaches |
| --- | --- | --- |
| `qa.jsonl` | 6–14 | Direct question answering over one work: metadata, cast, crew, episodes, relations, franchise, multi-hop, comparison |
| `instructions.jsonl` | 0–12 | Task formats: extraction, summarisation, JSON repair, title normalisation, entity resolution, abstention |
| `rag_chunks.jsonl` | 4–10 | Retrieval units written as prose, each with `source_refs` and a `kind` label |
| `descriptions.jsonl` | 1 | `record_summary`, generated from structured fields only |

**QA pairs** are emitted only when every value in the answer exists in the
database for that work. Each question type has several phrasings chosen
deterministically per work, so the corpus is not one repeated template. Roughly
one pair in twenty is an explicit abstention ("No episode count is recorded for
this work in this dataset") so a model can learn to decline instead of inventing.

**Instruction examples** are derivable from their own `input` field by
construction: the source facts are rendered into the input, then the task asks
for a transformation of exactly those facts. This is checked at validation time
by re-reading the input and confirming each output value appears in it.

**RAG chunks** are prose, not JSON dumps, and are labelled by family
(`record_summary`, `title_aliases`, `characters`, `voice_cast`,
`staff`, `episodes`, `relations`).

### What it is NOT

- No images, posters, audio, subtitles, or lyrics.
- No upstream plot synopses, character biographies or episode summaries.
  Those are third-party expression, so they are excluded from every export
  rather than paraphrased. See `LICENSE_AUDIT.md`.
- No full scripts or long copyrighted passages.
- No human-written question/answer pairs: the QA and instruction corpora are
  template-generated from structured fields. They are supervision for
  extraction and grounding, not a source of new facts.

---

## Coverage and known limits

These are measured, not estimated — the exact figures are regenerated into
[`reports/final_report.md`](reports/final_report.md) on every run.

- **Episode lists are the weakest field.** Kitsu is the only reachable source
  that publishes per-episode records. Shikimori's episode endpoint is
  unavailable, AniList publishes counts but not episode lists, and
  MyAnimeList/Jikan is network-blocked from the collection environment. Works
  without a Kitsu link therefore have an episode *count* but no episode *list*.
- **Depth is uneven by design.** Characters, staff and episodes exist only where
  an upstream source published them. The coverage table above gives the exact
  rate per field instead of an average that hides the spread.
- **The Anime News Network encyclopedia contributes zero rows.** It is reachable
  only page-by-page, so a sample was collected and retained in raw storage
  without being linked into the exports.
- **The 50,000-title target is not met.** The union of the reachable catalogues
  is exhausted at the current count; MAL would raise it and is blocked.
- **Franchise clusters use strong relations only** (`SEQUEL`, `PREQUEL`,
  `PARENT_STORY`, `FULL_STORY`, `SIDE_STORY`, `SPIN_OFF`,
  `ALTERNATIVE_SETTING`, `ALTERNATIVE_VERSION`, `SUMMARY`). Sharing a source
  manga or a cameo does not merge two works into one cluster.

---

## Ways to access, clone, or train

Eight ready-to-use gateways into the same data:

| # | Method | What you get | How |
| --- | --- | --- | --- |
| 1 | **Clone the repository** | code, schemas, docs, pipeline | `git clone <repo-url>` |
| 2 | **Download release assets** | the full `exports/` tree | GitHub Releases (browser or `gh release download`) |
| 3 | **Stream JSONL in Python** | train-ready rows without loading everything | loop over `open("exports/qa.jsonl", encoding="utf-8")` |
| 4 | **Hugging Face `datasets` loader** | a sharded HF `Dataset` | `load_dataset("json", data_files=...)` |
| 5 | **SQLite database** | joins and referential queries | `sqlite3 exports/anime_dataset.sqlite` or Python stdlib |
| 6 | **Parquet + DuckDB / pandas** | fast analytics | `duckdb -c "select ..."` or `pd.read_parquet` |
| 7 | **CSV** | spreadsheet-friendly flat view | open `exports/anime.csv` |
| 8 | **Training recipes** | fine-tuned models | follow `docs/TRAINING.md` + `examples/` scripts |

Each gateway is covered with runnable code in [`docs/COMMANDS.md`](docs/COMMANDS.md)
(terminals) and [`docs/TRAINING.md`](docs/TRAINING.md) (model training).

---

## Formats and download

Primary format is **JSONL** (UTF-8, one logical record per line, deterministic field order, stable IDs). Derived formats are regenerated from the same canonical data.

| Format | File | Notes |
| --- | --- | --- |
| JSONL | `exports/*.jsonl` | canonical, 19 tables |
| SQLite | `exports/anime_dataset.sqlite` | all tables, `split` and `license_tier` pre-joined, indexed |
| Parquet | `exports/*.parquet` | 10 tables, for analytics |
| CSV | `exports/anime.csv` | flat anime table |
| License subsets | `exports/license_tier_*.csv` | pre-filtered anime id lists per tier |
| Checksums | `exports/checksums.json` + per-file `.sha256` | verify integrity |

Every per-anime table carries `split` and `license_tier` as columns, so a
training script can filter without joining anything. JSON arrays are real
arrays in JSONL and Parquet, not encoded strings.

> **Git note**: the multi-hundred-MB generated dataset ships as **release assets**, not commit payloads. Clone the repository for code, docs, and schemas; download the dataset archive from the GitHub Release for the full `exports/` tree. Every release publishes SHA-256 checksums.

Verified checksum verification (any shell):

```
# PowerShell
Get-ChildItem exports\*.jsonl | ForEach-Object {
  $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
  if ($h -eq (Get-Content "$($_.FullName).sha256").Split(' ')[0]) { "OK  $($_.Name)" } else { "BAD $($_.Name)" }
}
```

---

## Explore the data

Two ways to browse before training:

- **Interactive explorer site** — [`docs/explore.html`](docs/explore.html) renders the
  live statistical profile: coverage rates, year/type/status distributions,
  top genres, themes and studios, numeric quartiles for every length/score
  field, and the full export manifest.
- **Static profile** — [`reports/data_profile.json`](reports/data_profile.json)
  is the machine-readable version, regenerated any time with
  `python scripts/data_profile.py`.
- **EDA notebook** — [`examples/notebooks/EDA.ipynb`](examples/notebooks/EDA.ipynb)
  walks the same numbers in Jupyter with charts.
- **Publish to Hugging Face Hub** — `python scripts/upload_hf.py --repo <hf-user>/large-anime-text-dataset`
  uploads the release as a dataset repo with a generated card
  (`--dry-run` first, token via `HF_TOKEN`).

---

## Sources and licensing

| Source | Contributed | Terms | Tier assigned |
| --- | --- | --- | --- |
| **AniList** | discovery, scores, characters, staff, relations | public GraphQL API; terms allow API use, not redistribution of content | `permission_required` |
| **Kitsu** | discovery, episode lists | public JSON:API; terms grant no redistribution of API data | `permission_required` |
| **Shikimori** | discovery, cast, crew, relations | no license or terms for API data could be located | `unresolved` |
| **Wikidata** | supplementary titles | **CC0-1.0** | `cc0_only` |
| **ANN encyclopedia** | 789 sample pages, retained in raw storage | copyrighted | not linked into exports |
| **MyAnimeList / Jikan** | none | — | unreachable, excluded |

Each anime row is assigned exactly one tier: the **strictest** implied by the
sources that contributed to it (`unresolved` > `permission_required` >
`cc0_only`). The tier names describe the obligation you take on, not the
copyright status of the underlying anime, which stays with its rights holders.

- `cc0_only` — no obligation; attribution is courtesy.
- `permission_required` — AniList and Kitsu terms do not grant redistribution;
  obtain written permission before publishing derived records.
- `unresolved` — no permission basis identified; do not redistribute.

Machine-readable: `exports/license_tiers.jsonl` (per anime),
`exports/license_manifest.json` (definitions, counts, gaps, disclaimer),
`exports/sources.jsonl` (per source), `exports/provenance.jsonl` (per record).
Human-readable: [docs/LICENSE_NOTES.md](docs/LICENSE_NOTES.md), [NOTICE](NOTICE),
[ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

The repository code, pipeline and generated text are released under
**[CC-BY-4.0](LICENSE)**. That license covers the code and the text this project
generates; it cannot and does not relicense upstream source content.

**No upstream prose ships.** Plot synopses, character biographies and episode
summaries are third-party expression and no source terms grant redistribution,
so those fields are dropped from every export rather than paraphrased. Every
artifact and its rights status is listed in [LICENSE_AUDIT.md](LICENSE_AUDIT.md).

---

## Data objects

| Object | Export file | Content |
| --- | --- | --- |
| Anime | `anime.jsonl` | canonical record per unique work, with nested titles/genres/themes/studios/sources |
| Characters | `characters.jsonl` | name, native name, localized name, role, voice actors |
| Staff | `staff.jsonl` | person, credit roles, source references |
| Studios | `studios.jsonl` | studio names + identifiers |
| Genres / themes | `genres.jsonl`, `themes.jsonl` | controlled vocabulary |
| Episodes | `episodes.jsonl` | number, title, air date, runtime |
| Relationships | `relationships.jsonl` | typed edges between works |
| Alternative titles | `alt_titles.jsonl` | language, kind, and the sources that supplied it |
| Descriptions | `descriptions.jsonl` | `record_summary` only, with provenance |
| QA pairs | `qa.jsonl` | question, answer, type, template, grounded fields |
| Instructions | `instructions.jsonl` | instruction, input, output, type, purpose |
| RAG chunks | `rag_chunks.jsonl` | prose chunk, `kind`, `source_refs` |
| Entity links | `entity_links.jsonl` | internal → external IDs, method, confidence |
| Franchises | `franchises.jsonl` | anime → franchise cluster id |
| Provenance | `provenance.jsonl` + `sources.jsonl` | per-record + source registry |
| License tiers | `license_tiers.jsonl` | per-anime redistribution tier and reason |

### The `anime` record schema

| Field | Type | Meaning |
| --- | --- | --- |
| `anime_id` | int | stable internal ID |
| `type` | enum | `TV`, `MOVIE`, `OVA`, `ONA`, `SPECIAL`, `TV_SPECIAL`, `SHORT`, `TV_SHORT`, `ONA_SHORT`, `MUSIC`, `PV`, `CM` |
| `status` | enum | `FINISHED`, `RELEASING`, `NOT_YET_RELEASED`, `CANCELLED`, `HIATUS` |
| `episodes`, `duration_min` | int | episode count and per-episode minutes |
| `aired_from`, `aired_to` | date | air window (`YYYY-MM-DD`) |
| `season`, `year` | enum/int | `WINTER`/`SPRING`/`SUMMER`/`FALL` and start year |
| `title_canonical`, `title_english`, `title_japanese` | string | titles |
| `mean_score`, `popularity`, `favourites` | number | score on a single normalised 0–100 scale |
| `source_material`, `age_rating` | enum | e.g. `MANGA`, `PG-13` |
| `quality_tier` | string | A / B / C |
| `confidence` | string | high/medium/low |
| `alt_titles`, `genres`, `themes`, `studios`, `sources`, `franchise_id`, `license_tier`, `split` | list/string | enriched record |

Full field-level reference: [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) and [`docs/SCHEMAS.md`](docs/SCHEMAS.md).

---

## Train / validation / test splits

- **90 / 5 / 5** (train / val / test), random seed **42**.
- Split **per anime**, never per record — every character, QA pair, chunk, and relationship of a work lands in the same bucket, so **no leakage** across train/test.
- Every exported record carries its `split` so you can filter without re-walking the tables.

```python
import json
train_qa = [q for q in map(json.loads, open("exports/qa.jsonl", encoding="utf-8")) if q["split"] == "train"]
val_qa   = [q for q in map(json.loads, open("exports/qa.jsonl", encoding="utf-8")) if q["split"] == "val"]
test_qa  = [q for q in map(json.loads, open("exports/qa.jsonl", encoding="utf-8")) if q["split"] == "test"]
```

---

## Quick start: run commands in terminals

Works identically from **Windows CMD**, **PowerShell**, and **Git Bash / WSL**. Replace `python` with `python3` where your system uses it.

### 1. Clone and install

```bash
git clone <repo-url>
cd anime-text-dataset
python -m venv .venv
.venv\Scripts\activate        # Windows CMD/PowerShell
# source .venv/bin/activate  # Git Bash / WSL / macOS
pip install -r requirements.txt
```

### 2. Explore the dataset (no training required)

```bash
python -m src.cli validate       # run all 21 validation checks
python -m src.cli checksums      # regenerate SHA-256 checksums
python -m src.cli report         # regenerate reports/final_report.md + summary.json
python scripts/sync_docs.py      # refresh the generated tables in the docs
```

### 3. Train a model

The full guide — SFT, LoRA/QLoRA, DPO, RAG fine-tuning, continual pretraining, embeddings, classifiers — lives in **[`docs/TRAINING.md`](docs/TRAINING.md)**.

---

## Command-line reference

| Command | Phase | Description |
| --- | --- | --- |
| `python -m src.cli discover` | P0 | collect payloads per source |
| `python -m src.cli dedup` | P1 | entity resolution → canonical anime rows |
| `python -m src.cli backfill` | P1 | fill missing fields from stored payloads |
| `python -m src.cli refill` | P1 | re-fetch stale or failed payloads |
| `python -m src.cli enrich` | P2 | full metadata for the depth tier |
| `python -m src.cli entities` | P3 | materialize characters, staff, studios, episodes |
| `python -m src.cli normalize` | P3.5 | merge duplicates, canonicalize enums, repair values, dedupe entities |
| `python -m src.cli relationships` | P4 | derive relationship edges |
| `python -m src.cli franchise` | P5 | cluster works into franchises |
| `python -m src.cli descriptions` | P6 | write record summaries |
| `python -m src.cli qa` | P7 | generate QA pairs |
| `python -m src.cli instructions` | P8 | generate instruction-tuning examples |
| `python -m src.cli rag` | P9 | build RAG chunks with source refs |
| `python -m src.cli split` | P10 | assign train/val/test per anime |
| `python scripts/license_tiers.py` | P11 | assign license tiers in the DB, write manifest and subsets |
| `python -m src.cli export` | P12 | write JSONL/SQLite/Parquet/CSV with `split` + `license_tier` joined |
| `python -m src.cli validate` | QA | run all 21 validation checks |
| `python -m src.cli checksums` | QA | refresh SHA-256 checksums |
| `python -m src.cli report` | QA | regenerate the report |
| `python scripts/sync_docs.py` | QA | refresh generated doc tables from the report |

Order matters in two places: `license_tiers` runs **before** `export` so the
tier is a real column in the exported rows rather than a null, and `validate`
runs **after** `export` because it checks the exported files.

> Full flag and environment details: [`docs/COMMANDS.md`](docs/COMMANDS.md).

---

## Explore the data from the terminal

```bash
# Count rows (PowerShell)
(Get-Content exports\anime.jsonl | Measure-Object -Line).Lines
# Count rows (Git Bash / WSL / macOS)
wc -l exports/anime.jsonl

# Stream one record
Get-Content exports\anime.jsonl -TotalCount 1   # PowerShell

# Python query (zero extra deps)
python -c "import json; A=[json.loads(l) for l in open('exports/anime.jsonl',encoding='utf-8')]; print(len(A), sum(1 for a in A if a['year']==2020))"

# SQLite query (Python stdlib, no install)
python -c "import sqlite3; con=sqlite3.connect('exports/anime_dataset.sqlite'); [print(r) for r in con.execute('select year,count(*) from anime group by year order by 2 desc limit 5')]"

# DuckDB over Parquet (pip install duckdb)
duckdb -c "select year, count(*) n from read_parquet('exports/anime.parquet') group by year order by year desc limit 5;"

# Only commercially usable rows
python -c "import csv; ids={r['anime_id'] for r in csv.DictReader(open('exports/license_commercial_clear.csv',encoding='utf-8'))}; print(len(ids), 'anime in the clear subset')"
```

---

## How to train models on this dataset

Nine concrete training recipes:

| # | Recipe | Output | Key files |
| --- | --- | --- | --- |
| 1 | Instruction fine-tuning (SFT) | chat-style assistant | `qa.jsonl`, `instructions.jsonl` |
| 2 | Parameter-efficient fine-tuning (LoRA / QLoRA) | small-GPU fine-tune | `instructions.jsonl` |
| 3 | Preference tuning (DPO) | grounded responses | `qa.jsonl` |
| 4 | Retrieval-augmented generation (RAG) fine-tune | grounded QA | `rag_chunks.jsonl`, `qa.jsonl` |
| 5 | Domain continual pretraining | anime-proficient base model | `descriptions.jsonl` |
| 6 | Contrastive / embedding training | semantic retrieval | `rag_chunks.jsonl`, `qa.jsonl` |
| 7 | Classification & ranking heads | genre/source/rating predictors | `anime.jsonl` |
| 8 | Entity linking & relation extraction | KG construction | `entity_links.jsonl`, `relationships.jsonl` |
| 9 | Evaluation & benchmarks | honest model reporting | all test-split files |

Complete code, environment setup, hardware notes, and evaluation guidance: **[`docs/TRAINING.md`](docs/TRAINING.md)** — the single authoritative guide.

---

## Load the data in Python

```python
import json, sqlite3
import pandas as pd

# JSONL → dicts
anime = [json.loads(l) for l in open("exports/anime.jsonl", encoding="utf-8")]
by_id = {a["anime_id"]: a for a in anime}

# Search by title
hits = [a for a in anime if "Cowboy" in (a.get("title_canonical") or "")]

# SQLite
con = sqlite3.connect("exports/anime_dataset.sqlite")
rows = con.execute(
    "select title_canonical, year from anime "
    "where year >= 2015 order by mean_score desc limit 10"
).fetchall()

# Parquet via pandas
df = pd.read_parquet("exports/anime.parquet")
df[df["year"] == 1998].head()

# QA training stream, filtered to one license tier
for line in open("exports/qa.jsonl", encoding="utf-8"):
    q = json.loads(line)
    if q["split"] == "train" and q["license_tier"] == "cc0_only":
        pass  # feed (q["question"], q["answer"]) to your trainer
```

---

## Frequently asked questions

**Can I train an LLM on this?** Yes — that is the primary use case. `qa.jsonl` and `instructions.jsonl` are ready-to-shard instruction formats; see `docs/TRAINING.md`.

**Which part do I use for what?** QA/instructions → chat fine-tuning; RAG chunks → retrieval; anime records → classification/ranking; relationships → knowledge-graph and relation extraction.

**Is there leakage across train/test?** No — splits are assigned per anime, so all records of one work stay in one bucket.

**Can I publish a model trained on this?** Check the `license_tier` column first. Only `cc0_only` rows have no upstream permission outstanding; `permission_required` and `unresolved` rows carry obligations that this project cannot discharge for you. This is an organisational aid, not legal advice.

**Why are some answers "not recorded"?** About one QA pair in twenty is a deliberate abstention for a field that is genuinely absent, so a model can learn to decline rather than guess.

---

## Citation

```bibtex
@software{anime_text_dataset,
  author    = {Muhammad Muqeet},
  title     = {Large Anime Text Dataset},
  year      = {2026},
  version   = {2.0.0},
  note      = {Large anime text dataset; see reports/summary.json for exact row counts. Contact: muqeet@animearray.site; muqeet@anitroves.com}
}
```

Machine-readable: [`CITATION.cff`](CITATION.cff).

---

## License

The repository code, pipeline, and generated text are licensed under
**[CC-BY-4.0](LICENSE)**. Upstream source content is not relicensed by that
license: every anime row carries a `license_tier` derived from the sources that
contributed to it, and `exports/license_manifest.json` states what each tier
permits. No upstream prose is shipped; the per-artifact audit is
[LICENSE_AUDIT.md](LICENSE_AUDIT.md).
