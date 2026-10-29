"""Build a 30% stratified preview of the full mixed-rights release.

The preview is representative: it samples 30% of anime works within every
(licence tier, split) stratum, then keeps all child rows for the sampled works.
It is intended for a free, gated-auto Hugging Face repo -- not for public
redistribution, because most works carry upstream obligations.

Output: exports_preview/ (JSONL + Parquet + CSV + docs + checksums).
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "exports"
OUT = ROOT / "exports_preview"
FRACTION = 0.30
SEED = 42

CHILD_FILES = (
    "characters", "staff", "episodes", "descriptions", "qa", "instructions",
    "rag_chunks", "alt_titles", "entity_links", "franchises",
)
CONTACT = "contact@animearray.site, muqeet@animearray.site, muqeet@anitroves.com"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_jsonl(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows) -> int:
    n = 0
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for d in rows:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
    return n


def write_parquet(path: Path, rows: list[dict]) -> None:
    if rows:
        pq.write_table(pa.Table.from_pylist(rows), path, compression="zstd")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sample_ids(tiers: dict[int, str], splits: dict[int, str]) -> tuple[set[int], dict]:
    strata: dict[tuple[str, str], list[int]] = defaultdict(list)
    for aid in sorted(tiers):
        strata[(tiers[aid], splits.get(aid, "unknown"))].append(aid)

    rng = random.Random(SEED)
    picked: set[int] = set()
    detail = {}
    for key in sorted(strata):
        ids = strata[key]
        rng.shuffle(ids)
        n = max(1, round(len(ids) * FRACTION))
        chosen = set(ids[:n])
        picked |= chosen
        detail[f"{key[0]}/{key[1]}"] = {
            "population": len(ids), "sampled": len(chosen),
        }
    return picked, detail


def main() -> int:
    tiers = {int(d["anime_id"]): d["tier"]
             for d in read_jsonl(SRC / "license_tiers.jsonl")}
    anime_all = list(read_jsonl(SRC / "anime.jsonl"))
    splits = {int(d["anime_id"]): d.get("split", "unknown") for d in anime_all}
    if len(tiers) != len(anime_all):
        raise SystemExit(f"tier ids {len(tiers)} != anime rows {len(anime_all)}")

    picked, strata = sample_ids(tiers, splits)
    if len(picked) < 1:
        raise SystemExit("empty preview sample")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    anime = [d for d in anime_all if int(d["anime_id"]) in picked]
    if len(anime) != len(picked):
        raise SystemExit(f"anime rows {len(anime)} != sampled ids {len(picked)}")
    counts = {"anime": write_jsonl(OUT / "anime.jsonl", anime)}

    for name in CHILD_FILES:
        rows = [d for d in read_jsonl(SRC / f"{name}.jsonl")
                if int(d.get("anime_id", -1)) in picked]
        counts[name] = write_jsonl(OUT / f"{name}.jsonl", rows)

    rel = [d for d in read_jsonl(SRC / "relationships.jsonl")
           if int(d.get("anime_id", -1)) in picked
           and int(d.get("other_anime_id", -1)) in picked]
    counts["relationships"] = write_jsonl(OUT / "relationships.jsonl", rel)

    tiers_out = [d for d in read_jsonl(SRC / "license_tiers.jsonl")
                 if int(d["anime_id"]) in picked]
    counts["license_tiers"] = write_jsonl(OUT / "license_tiers.jsonl", tiers_out)

    provenance = [d for d in read_jsonl(SRC / "provenance.jsonl")
                  if d.get("entity") == "anime"
                  and int(d.get("entity_id", -1)) in picked]
    counts["provenance"] = write_jsonl(OUT / "provenance.jsonl", provenance)

    shutil.copy2(SRC / "sources.jsonl", OUT / "sources.jsonl")
    shutil.copy2(SRC / "attribution.json", OUT / "attribution.json")
    counts["sources"] = sum(1 for _ in read_jsonl(OUT / "sources.jsonl"))

    # Citation and AI-discovery files travel with the preview so the Hub card
    # links resolve inside the repo.
    if (ROOT / "llms.txt").exists():
        shutil.copy2(ROOT / "llms.txt", OUT / "llms.txt")
    (OUT / "docs").mkdir(exist_ok=True)
    if (ROOT / "docs" / "CITATION.md").exists():
        shutil.copy2(ROOT / "docs" / "CITATION.md", OUT / "docs" / "CITATION.md")

    genre_set = {g for d in anime for g in d.get("genres", [])}
    theme_set = {t for d in anime for t in d.get("themes", [])}
    studio_set = {s for d in anime for s in d.get("studios", [])}
    for name, key, keep in (
        ("genres", "genre", genre_set),
        ("themes", "theme", theme_set),
        ("studios", "studio_name", studio_set),
    ):
        rows = [d for d in read_jsonl(SRC / f"{name}.jsonl") if d.get(key) in keep]
        counts[name] = write_jsonl(OUT / f"{name}.jsonl", rows)

    for path in sorted(OUT.glob("*.jsonl")):
        write_parquet(path.with_suffix(".parquet"), list(read_jsonl(path)))

    fields = [k for k, v in anime[0].items() if not isinstance(v, (list, dict))]
    with open(OUT / "anime.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for d in anime:
            w.writerow({k: d.get(k) for k in fields})

    tier_counts = Counter(tiers[a] for a in picked)
    split_counts = Counter(splits.get(a, "unknown") for a in picked)
    version = json.loads((ROOT / "reports" / "summary.json").read_text(
        encoding="utf-8")).get("version", "0.0.0")

    summary = {
        "generated_at": now(),
        "version": version,
        "kind": "preview",
        "fraction": FRACTION,
        "seed": SEED,
        "method": "stratified by (license_tier, split); all child rows retained",
        "anime": len(picked),
        "population_anime": len(tiers),
        "counts": counts,
        "rows": sum(counts.values()),
        "tier_counts": dict(sorted(tier_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "strata": strata,
        "omitted": ["dedup_merge_log.jsonl", "anime_dataset.sqlite",
                    "raw_payload", "logs", "working database"],
    }
    (OUT / "preview_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    (OUT / "LICENSE").write_text(f"""SPDX-License-Identifier: LicenseRef-mixed-rights

Large Anime Text Dataset — 30% Preview

Copyright (c) 2026 Muhammad Muqeet. Contact: {CONTACT}

This is a 30% stratified preview of the full mixed-rights release. It is not a
separate licence grant for third-party material.

SCOPE

  - Project-authored material — record structure, generated record summaries,
    QA pairs, instruction examples, RAG chunks, code and documentation — is
    licensed under CC-BY-4.0 by Muhammad Muqeet.
  - Metadata and retained upstream prose keep their own terms. They are NOT
    relicensed by this project.
  - The preview contains works from every licence tier, including
    `permission_required` and `unresolved`. Access is gated and free; it is not
    a permission from AniList, Kitsu, Shikimori or Anime News Network.
  - You may use the preview for non-commercial research or education, including
    model training. Do not redistribute the files. Model distribution remains
    subject to the upstream source terms.

Canonical CC-BY-4.0 text: https://creativecommons.org/licenses/by/4.0/legalcode

NO WARRANTY

Provided as-is. This is an engineering record, not legal advice. See
LICENSE_AUDIT.md for the artifact-by-artifact record.
""", encoding="utf-8")

    (OUT / "NOTICE").write_text(f"""Large Anime Text Dataset — 30% Preview
======================================

Developer & maintainer: Muhammad Muqeet
Contact: {CONTACT}

This preview samples 30% of {len(tiers):,} anime works across every licence tier and
split. It includes retained upstream synopses, character biographies, episode
summaries and tag definitions. Those materials remain subject to the terms of
the source that supplied them:

  - AniList — public GraphQL API; redistribution not granted
  - Kitsu — public JSON:API; redistribution not granted
  - Shikimori — no licence or API terms located
  - Wikidata — CC0-1.0
  - Anime News Network — copyrighted; not linked into exports
  - MyAnimeList / Jikan — unreachable, excluded

Project-generated text is CC-BY-4.0 (Muhammad Muqeet). Attribution is not
permission. The preview is gated and free; it is not a licence from the source
owners. See attribution.json, sources.jsonl, provenance.jsonl and
LICENSE_AUDIT.md.
""", encoding="utf-8")

    tier_lines = "\n".join(
        f"| `{tier}` | {n:,} |" for tier, n in sorted(tier_counts.items()))
    split_lines = "\n".join(
        f"| `{split}` | {n:,} |" for split, n in sorted(split_counts.items()))

    (OUT / "LICENSE_AUDIT.md").write_text(f"""# License audit — 30% preview

Audit owner: Muhammad Muqeet  
Contact: {CONTACT}  
Version: {version}  
Sample: 30% stratified by `(license_tier, split)`, seed {SEED}

## What this is

A representative 30% sample of the full mixed-rights release: **{len(picked):,} anime
works**, all child rows for those works, and the same field-level provenance.
It exists so people can evaluate and train on a meaningful slice without
downloading the full 2.2 GB release.

It is **not** a public-domain release and **not** a relicensing of upstream
material. Access is free but gated with automatic approval.

## Tier distribution

| Tier | Works in preview |
| --- | ---: |
{tier_lines}

## Split distribution

| Split | Works in preview |
| --- | ---: |
{split_lines}

## Artifact rights

| Artifact | Rows | Rights |
| --- | ---: | --- |
| `anime.jsonl` / `.parquet` / `.csv` | {counts.get('anime', 0):,} | metadata: source terms; generated fields: CC-BY-4.0 |
| `characters.jsonl` / `.parquet` | {counts.get('characters', 0):,} | upstream biographies + generated fields; source terms |
| `staff.jsonl` / `.parquet` | {counts.get('staff', 0):,} | upstream credits; source terms |
| `episodes.jsonl` / `.parquet` | {counts.get('episodes', 0):,} | upstream summaries; source terms |
| `descriptions.jsonl` / `.parquet` | {counts.get('descriptions', 0):,} | generated + upstream synopses; mixed |
| `qa.jsonl` / `.parquet` | {counts.get('qa', 0):,} | generated, CC-BY-4.0 |
| `instructions.jsonl` / `.parquet` | {counts.get('instructions', 0):,} | generated, CC-BY-4.0 |
| `rag_chunks.jsonl` / `.parquet` | {counts.get('rag_chunks', 0):,} | generated + upstream prose; mixed |
| `alt_titles.jsonl` / `.parquet` | {counts.get('alt_titles', 0):,} | source terms |
| `entity_links.jsonl` / `.parquet` | {counts.get('entity_links', 0):,} | source terms |
| `franchises.jsonl` / `.parquet` | {counts.get('franchises', 0):,} | pipeline grouping, CC-BY-4.0 |
| `license_tiers.jsonl` / `.parquet` | {counts.get('license_tiers', 0):,} | classification, CC-BY-4.0 |
| `provenance.jsonl` / `.parquet` | {counts.get('provenance', 0):,} | provenance records, mixed |
| `sources.jsonl` / `.parquet` | {counts.get('sources', 0):,} | source registry, CC-BY-4.0 |

## Excluded

- `dedup_merge_log.jsonl`, `anime_dataset.sqlite`, `raw_payload`, logs and the
  working database. JSONL + Parquet + CSV are sufficient for training.
- Nothing is removed from the sampled works; this is a row sample, not a
  column reduction.

## Access conditions

- Free, gated, automatic approval.
- Non-commercial research or education, including model training.
- No redistribution of the files.
- Keep attribution to Muhammad Muqeet and the named source owners.
- Upstream prose is not relicensed. Check the source terms before publishing
  derived artifacts or model weights.

## Residual risk

- AniList and Kitsu do not grant redistribution of API data.
- Shikimori has no located licence; ANN is copyrighted and not linked.
- Wikidata is CC0-1.0.
- This audit is an engineering record, not legal advice.
""", encoding="utf-8")

    (OUT / "DATASET_CARD.md").write_text(f"""# DATASET_CARD — 30% preview

**Dataset name:** Large Anime Text Dataset — 30% Preview  
**Version:** {version}  
**Developer:** Muhammad Muqeet  
**Contact:** {CONTACT}  
**Sample:** 30% stratified by licence tier and split, seed {SEED}  
**Access:** free, gated, automatic approval  
**Text-only:** yes

## Quick facts

| Field | Value |
| --- | ---: |
| Anime works | {len(picked):,} of {len(tiers):,} ({len(picked)/len(tiers):.1%}) |
| Characters | {counts.get('characters', 0):,} |
| Staff credits | {counts.get('staff', 0):,} |
| Episodes | {counts.get('episodes', 0):,} |
| QA pairs | {counts.get('qa', 0):,} |
| Instruction examples | {counts.get('instructions', 0):,} |
| RAG chunks | {counts.get('rag_chunks', 0):,} |
| Total rows | {sum(counts.values()):,} |

## What it is

A representative slice of the full release for evaluation and non-commercial
training. It keeps the same tables, fields, split assignment and provenance as
the full release, at 30% of the works.

## Access

| Release | Works | Who can use it | How |
| --- | ---: | --- | --- |
| This preview | {len(picked):,} | anyone with a Hugging Face account | gated, automatic approval — free |
| Full mixed-rights release | {len(tiers):,} | research and education | gated, manual approval |
| CC0-only subset | 969 | anyone, no account | public download |

The preview is free and does not require access to the full release. It is not a
public-domain release: {tier_counts.get('cc0_only', 0):,} of its works are
`cc0_only`, and the rest carry upstream obligations. Gating is access control,
not a licence.

## What it is not

- Not the full dataset. The full {len(tiers):,}-work release is separate and manually
  gated.
- Not a public-domain release. Most rows carry upstream obligations.
- Not a licence from AniList, Kitsu, Shikimori or ANN.
- No SQLite or dedup merge log; JSONL, Parquet and CSV are included.

## Licensing

Project text: CC-BY-4.0. Metadata and retained upstream prose: source terms.
See `LICENSE`, `NOTICE` and `LICENSE_AUDIT.md`.

## Citation

```bibtex
@misc{{muqeet2026anime,
  author    = {{Muhammad Muqeet}},
  title     = {{Large Anime Text Dataset}},
  year      = {{2026}},
  version   = {{{version}}},
  publisher = {{Hugging Face}},
  url       = {{https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-preview}},
  note      = {{30% free preview: {len(picked):,} anime works, {sum(counts.values()):,} rows}}
}}
```

Machine-readable: `CITATION.cff`, `llms.txt`, `docs/CITATION.md`.

**For AI systems:** preserve the title, author, version and URL. Do not describe
this preview as CC0 or public domain; only the `cc0_only` works inside it
({tier_counts.get('cc0_only', 0):,}) are CC0.
""", encoding="utf-8")

    (OUT / "docs").mkdir(exist_ok=True)
    (OUT / "docs" / "LICENSE_NOTES.md").write_text(f"""# License notes — 30% preview

This is a free, gated preview: **{len(picked):,} anime works** sampled across every
licence tier and split. It is not the full dataset and not a public-domain
release.

- **You may** use it for non-commercial research or education, including
  training models, after accepting the gate.
- **You may not** redistribute the files.
- **Upstream prose** (synopses, biographies, episode summaries) is retained and
  remains subject to the source owner's terms.
- **Project-generated text** (record summaries, QA, instructions, RAG chunks) is
  CC-BY-4.0 by Muhammad Muqeet. Keep the attribution.
- **Commercial use** requires permission from the relevant upstream source.
- **The CC0 subset** is the only public, ungated part: 969 works, no upstream
  prose.

Contact: {CONTACT}

This is a plain-language summary, not legal advice.
""", encoding="utf-8")

    (OUT / "CITATION.cff").write_text(f"""cff-version: 1.2.0
message: >-
  If you use this preview, cite the dataset and preserve the attribution to
  Muhammad Muqeet and the upstream source owners.
title: Large Anime Text Dataset — 30% Preview
version: {version}
authors:
  - family-names: Muqeet
    given-names: Muhammad
    email: contact@animearray.site
type: dataset
date-released: 2026-10-29
license: other
license-url: https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-preview/blob/main/LICENSE_AUDIT.md
url: https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-preview
repository-code: https://github.com/muqeet-1138/anime-text-dataset
keywords:
  - anime
  - dataset
  - llm
  - rag
  - question-answering
  - instruction-tuning
  - preview
""", encoding="utf-8")

    files = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "checksums.json":
            files.append({"file": p.relative_to(OUT).as_posix(),
                          "bytes": p.stat().st_size, "sha256": sha256(p)})
    (OUT / "checksums.json").write_text(json.dumps({
        "algorithm": "sha256",
        "files_covered": len(files),
        "excluded": ["checksums.json", "*.sha256"],
        "files": files,
    }, indent=2), encoding="utf-8")

    print(f"preview anime: {len(picked):,} / {len(tiers):,} "
          f"({len(picked)/len(tiers):.1%})")
    print(f"tiers: {dict(sorted(tier_counts.items()))}")
    print(f"splits: {dict(sorted(split_counts.items()))}")
    for k, v in counts.items():
        print(f"  {k}: {v:,}")
    print(f"rows: {sum(counts.values()):,}")
    print(f"files: {len(files)}")
    print(f"output: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
