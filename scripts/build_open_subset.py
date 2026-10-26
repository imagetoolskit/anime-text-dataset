"""Build the public CC0-only subset of the release.

The full dataset is mixed-rights: most rows depend on AniList, Kitsu or
Shikimori terms. This script writes the part that has no outstanding permission
request -- works tiered `cc0_only` -- so it can be published without a gate.

Output: exports_open/ (JSONL + Parquet + CSV + attribution + checksums).
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "exports"
OUT = ROOT / "exports_open"

CHILD_FILES = (
    "characters", "staff", "episodes", "descriptions", "qa", "instructions",
    "rag_chunks", "alt_titles", "entity_links", "franchises",
)


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
    if not rows:
        return
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path, compression="zstd")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    tiers = {d["anime_id"]: d for d in read_jsonl(SRC / "license_tiers.jsonl")}
    cc0 = {aid for aid, d in tiers.items() if d["tier"] == "cc0_only"}
    if not cc0:
        raise SystemExit("no cc0_only rows found; run scripts/license_tiers.py first")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    anime = [d for d in read_jsonl(SRC / "anime.jsonl") if d["anime_id"] in cc0]
    if len(anime) != len(cc0):
        raise SystemExit(f"anime rows {len(anime)} != cc0 ids {len(cc0)}")

    # The public subset must not contain upstream prose. The tier guarantees
    # this, but verify it instead of trusting the label.
    prose_problems = []
    for d in anime:
        if d.get("synopsis"):
            prose_problems.append(f"anime:{d['anime_id']}")
    counts = {"anime": write_jsonl(OUT / "anime.jsonl", anime)}

    for name in CHILD_FILES:
        rows = [d for d in read_jsonl(SRC / f"{name}.jsonl")
                if d.get("anime_id") in cc0]
        if name == "descriptions":
            prose_problems += [f"descriptions:{d['anime_id']}" for d in rows
                               if d.get("kind") == "source_synopsis"]
        elif name == "qa":
            prose_problems += [f"qa:{d['anime_id']}" for d in rows
                               if d.get("qtype") == "synopsis"]
        elif name == "rag_chunks":
            prose_problems += [f"rag:{d['anime_id']}" for d in rows
                               if d.get("kind") == "source_synopsis"]
        counts[name] = write_jsonl(OUT / f"{name}.jsonl", rows)

    # Relations only when both ends are in the clean subset; otherwise the edge
    # would point at a work whose tier is not publishable.
    rel = [d for d in read_jsonl(SRC / "relationships.jsonl")
           if d.get("anime_id") in cc0 and d.get("other_anime_id") in cc0]
    counts["relationships"] = write_jsonl(OUT / "relationships.jsonl", rel)

    tiers_out = [tiers[aid] for aid in sorted(cc0)]
    counts["license_tiers"] = write_jsonl(OUT / "license_tiers.jsonl", tiers_out)

    provenance = [d for d in read_jsonl(SRC / "provenance.jsonl")
                  if d.get("entity") == "anime" and str(d.get("entity_id")) in
                  {str(a) for a in cc0}]
    counts["provenance"] = write_jsonl(OUT / "provenance.jsonl", provenance)

    shutil.copy2(SRC / "sources.jsonl", OUT / "sources.jsonl")
    shutil.copy2(SRC / "attribution.json", OUT / "attribution.json")
    counts["sources"] = sum(1 for _ in read_jsonl(OUT / "sources.jsonl"))

    # Reference tables: keep only labels used by the subset.
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

    # Parquet is what the Hub viewer uses. Build it from the filtered rows.
    for path in sorted(OUT.glob("*.jsonl")):
        rows = list(read_jsonl(path))
        write_parquet(path.with_suffix(".parquet"), rows)

    # A small CSV for spreadsheet users; nested values are JSON-encoded.
    if anime:
        fields = [k for k, v in anime[0].items() if not isinstance(v, (list, dict))]
        with open(OUT / "anime.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for d in anime:
                w.writerow({k: d.get(k) for k in fields})

    if prose_problems:
        raise SystemExit(f"cc0 subset contains prose: {prose_problems[:5]}")

    # Empty child tables would show up as empty configs on the Hub. Drop them
    # and record the omission instead of shipping zero-byte files.
    omitted_empty = []
    for path in sorted(OUT.glob("*.jsonl")):
        if path.stat().st_size == 0:
            omitted_empty.append(path.name)
            path.unlink()
            parquet = path.with_suffix(".parquet")
            if parquet.exists():
                parquet.unlink()

    version = json.loads((ROOT / "reports" / "summary.json").read_text(
        encoding="utf-8")).get("version", "0.0.0")
    summary = {
        "generated_at": now(),
        "version": version,
        "filter": "license_tier == 'cc0_only'",
        "anime": len(cc0),
        "counts": counts,
        "rows": sum(counts.values()),
        "omitted_empty": omitted_empty,
    }
    (OUT / "subset_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    manifest = {
        "generated_at": now(),
        "dataset": "Large Anime Text Dataset — CC0-only subset",
        "version": version,
        "filter": "license_tier == 'cc0_only'",
        "tiers": {"cc0_only": len(cc0)},
        "content_policy": {
            "upstream_prose": "none",
            "note": "No upstream synopsis, biography or episode summary is "
                    "included. Project-generated text is CC-BY-4.0; metadata "
                    "is CC0-1.0.",
        },
    }
    (OUT / "license_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    # The full release's LICENSE says upstream prose is retained. That is false
    # for this subset, so write subset-specific licence and audit documents
    # instead of copying them.
    (OUT / "LICENSE").write_text(f"""SPDX-License-Identifier: CC-BY-4.0

Large Anime Text Dataset — CC0-only subset

Copyright (c) 2026 Muhammad Muqeet. Attribution for reuse of project-authored
material: "Muhammad Muqeet, Large Anime Text Dataset" with a link to
https://animearray.site or this repository, and contact
muqeet@animearray.site / muqeet@anitroves.com.

SCOPE

This subset contains {len(cc0):,} anime works whose every contributing source is
CC0-1.0. It contains no upstream synopsis, character biography, episode summary
or tag definition.

  - Project-authored material — record structure, generated record summaries,
    QA pairs, instruction examples, RAG chunks, code and documentation — is
    licensed under Creative Commons Attribution 4.0 International (CC-BY-4.0).
  - Metadata (titles, dates, counts, identifiers) is CC0-1.0, sourced from
    Wikidata.
  - No permission request is outstanding for any row in this subset.

Canonical CC-BY-4.0 text: https://creativecommons.org/licenses/by/4.0/legalcode
CC0-1.0 text: https://creativecommons.org/publicdomain/zero/1.0/legalcode

NO WARRANTY

The subset is provided as-is. It is not legal advice. See LICENSE_AUDIT.md for
the artifact-by-artifact record.
""", encoding="utf-8")

    (OUT / "NOTICE").write_text(f"""Large Anime Text Dataset — CC0-only subset
==========================================

Developer & maintainer: Muhammad Muqeet
Contact: muqeet@animearray.site, muqeet@anitroves.com

This subset contains {len(cc0):,} anime works. Every contributing metadata source is
CC0-1.0:

  - Wikidata (https://www.wikidata.org) — CC0-1.0

Project-generated text is CC-BY-4.0 (Muhammad Muqeet).

No AniList, Kitsu, Shikimori or Anime News Network prose is included. The full
mixed-rights release is a separate, gated repository.

Attribution and per-entity provenance:
  attribution.json, sources.jsonl, provenance.jsonl, LICENSE_AUDIT.md.
""", encoding="utf-8")

    (OUT / "LICENSE_AUDIT.md").write_text(f"""# License audit — CC0-only subset

Audit owner: Muhammad Muqeet  
Contact: muqeet@animearray.site, muqeet@anitroves.com  
Version: {version}

## The claim

> This subset contains {len(cc0):,} anime works tiered `cc0_only`. Their metadata is
> CC0-1.0 from Wikidata; the generated text, structure and documentation are
> CC-BY-4.0 by Muhammad Muqeet. No upstream prose is included.

## What is included

| Artifact | Rows | Rights |
| --- | ---: | --- |
| `anime.jsonl` / `.parquet` / `.csv` | {counts.get('anime', 0):,} | metadata CC0-1.0; generated fields CC-BY-4.0 |
| `descriptions.jsonl` / `.parquet` | {counts.get('descriptions', 0):,} | generated `record_summary`, CC-BY-4.0 |
| `qa.jsonl` / `.parquet` | {counts.get('qa', 0):,} | generated, CC-BY-4.0 |
| `instructions.jsonl` / `.parquet` | {counts.get('instructions', 0):,} | generated, CC-BY-4.0 |
| `rag_chunks.jsonl` / `.parquet` | {counts.get('rag_chunks', 0):,} | generated, CC-BY-4.0 |
| `entity_links.jsonl` / `.parquet` | {counts.get('entity_links', 0):,} | Wikidata links, CC0-1.0 |
| `franchises.jsonl` / `.parquet` | {counts.get('franchises', 0):,} | pipeline grouping, CC-BY-4.0 |
| `license_tiers.jsonl` / `.parquet` | {counts.get('license_tiers', 0):,} | classification, CC-BY-4.0 |
| `provenance.jsonl` / `.parquet` | {counts.get('provenance', 0):,} | provenance records, CC0-1.0 |
| `sources.jsonl` / `.parquet` | {counts.get('sources', 0):,} | source registry, CC-BY-4.0 |

## What is excluded

- All upstream prose: synopses, character biographies, episode summaries and
  tag definitions. Measured count in this subset: **0**.
- Characters, staff, episodes, alternative titles and relation edges: these
  tables are empty for the CC0 works and are omitted rather than shipped as
  zero-byte files.
- `raw_payload`, the working database, caches and logs.
- Every row not tiered `cc0_only`.

## How to verify

```bash
python scripts/build_open_subset.py
python scripts/upload_hf.py --repo <user>/anime-text-dataset-open --source exports_open --dry-run
```

`build_open_subset.py` fails if a prose row appears in the subset, and writes
`checksums.json` for every shipped file.

## Residual risk

- Wikidata is CC0-1.0; attribution is courtesy, not an obligation.
- Generated text is project-authored but derived from Wikidata facts. It adds no
  plot detail.
- This audit is an engineering record, not legal advice.
""", encoding="utf-8")

    (OUT / "DATASET_CARD.md").write_text(f"""# DATASET_CARD — CC0-only subset

**Dataset name:** Large Anime Text Dataset — CC0-only subset  
**Version:** {version}  
**Developer:** Muhammad Muqeet  
**Contact:** muqeet@animearray.site, muqeet@anitroves.com  
**Text-only:** yes  
**Filter:** `license_tier == 'cc0_only'`

## Quick facts

| Field | Value |
| --- | ---: |
| Unique anime works | {len(cc0):,} |
| Description rows | {counts.get('descriptions', 0):,} |
| QA pairs | {counts.get('qa', 0):,} |
| Instruction examples | {counts.get('instructions', 0):,} |
| RAG chunks | {counts.get('rag_chunks', 0):,} |
| Entity links | {counts.get('entity_links', 0):,} |
| Provenance rows | {counts.get('provenance', 0):,} |
| Upstream prose rows | 0 |

## What it is

A small, fully reusable slice of the larger anime corpus. Every work is
CC0-1.0 metadata from Wikidata, plus project-generated text assembled from
those facts. It is suitable for schema exploration, smoke tests, teaching and
any use that needs no permission request.

## What it is not

- Not the full corpus. The full 35,766-work release is separate and gated.
- No character biographies, episode summaries, cast lists or relation edges:
  those fields come from sources that are not CC0 for these works.
- No upstream prose of any kind.
- Not a source of new plot facts; generated text is template-based.

## Licensing

Metadata: CC0-1.0 (Wikidata). Project-authored text and structure: CC-BY-4.0.
See `LICENSE`, `NOTICE` and `LICENSE_AUDIT.md`.
""", encoding="utf-8")

    (OUT / "docs").mkdir(exist_ok=True)
    (OUT / "docs" / "LICENSE_NOTES.md").write_text(f"""# License notes — CC0-only subset

This subset is the part of the dataset with no outstanding permission request:
{len(cc0):,} anime works tiered `cc0_only`.

- **Metadata** is CC0-1.0 from Wikidata. You can reuse it freely.
- **Generated text** (record summaries, QA, instructions, RAG chunks) is
  CC-BY-4.0 by Muhammad Muqeet. Keep the attribution.
- **No upstream prose** is included. There are zero synopses, biographies,
  episode summaries or tag definitions in this subset.
- The full 35,766-work release is separate and gated because most of it depends
  on AniList, Kitsu or Shikimori terms.

Attribution: "Muhammad Muqeet, Large Anime Text Dataset", with a link to
https://animearray.site or the repository, and contact
muqeet@animearray.site / muqeet@anitroves.com.

This is a plain-language summary, not legal advice.
""", encoding="utf-8")

    src = ROOT / "CITATION.cff"
    if src.exists():
        shutil.copy2(src, OUT / "CITATION.cff")

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

    print(f"cc0 anime: {len(cc0):,}")
    for k, v in counts.items():
        print(f"  {k}: {v:,}")
    print(f"rows: {sum(counts.values()):,}")
    print(f"files: {len(files)}")
    print(f"output: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
