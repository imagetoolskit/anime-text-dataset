"""Publish a release directory to the Hugging Face Hub as a dataset repo.

Uploads the data files, the generated dataset card, the licence/attribution
records and the release summary. The full mixed-rights release should be gated;
the CC0-only subset can be public.

Usage:
    python scripts/upload_hf.py --repo <user>/<repo> [--source exports]
                                [--gated manual] [--private] [--dry-run]
                                [--tag v2.1.0] [--token $HF_TOKEN]

The token is read from --token, HF_TOKEN, or the session saved by
`huggingface-cli login`, and is never logged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "exports"
DATA_SUFFIXES = {".jsonl", ".parquet", ".csv", ".sqlite", ".json"}
DOC_SUFFIXES = {".md", ".cff"}
DOC_FILES = ("LICENSE", "NOTICE", "LICENSE_AUDIT.md", "DATASET_CARD.md",
             "CITATION.cff", "llms.txt")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_checksums(source: Path) -> list[str]:
    """Return mismatches between checksums.json and the files on disk."""
    manifest = source / "checksums.json"
    if not manifest.exists():
        return ["checksums.json missing"]
    data = load_json(manifest)
    problems = []
    for entry in data.get("files", []):
        path = source / entry["file"]
        if not path.exists():
            problems.append(f"{entry['file']}: missing")
            continue
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != entry["sha256"]:
            problems.append(f"{entry['file']}: sha256 mismatch")
    return problems


def collect_uploads(source: Path, include_only: list[str] | None) -> list[tuple[Path, str]]:
    """Return (local path, path in repo), source files first."""
    uploads: dict[str, Path] = {}
    for p in sorted(source.iterdir()):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.name == "README.md":
            continue
        if (p.suffix.lower() not in DATA_SUFFIXES
                and p.suffix.lower() not in DOC_SUFFIXES
                and p.name not in ("LICENSE", "NOTICE")):
            continue
        if include_only:
            stem = p.stem
            if stem not in include_only and p.name not in include_only:
                continue
        uploads[p.name] = p

    # A release directory may ship its own licence documents (the CC0 subset
    # does). Those must win over the full-release root documents.
    local_notes = source / "docs" / "LICENSE_NOTES.md"
    if local_notes.exists():
        uploads["docs/LICENSE_NOTES.md"] = local_notes
    for name in DOC_FILES:
        p = ROOT / name
        if p.exists() and name not in uploads:
            uploads[name] = p
    notes = ROOT / "docs" / "LICENSE_NOTES.md"
    if notes.exists():
        uploads.setdefault("docs/LICENSE_NOTES.md", notes)
    citation = ROOT / "docs" / "CITATION.md"
    if citation.exists():
        uploads.setdefault("docs/CITATION.md", citation)
    summary = source / "subset_summary.json"
    if not summary.exists() and not (source / "preview_summary.json").exists():
        full = ROOT / "reports" / "summary.json"
        if full.exists():
            uploads.setdefault("summary.json", full)
    return [(p, rel) for rel, p in sorted(uploads.items())]


def configs_block(source: Path) -> str:
    names = sorted(p.stem for p in source.glob("*.parquet"))
    if not names:
        return ""
    lines = ["configs:"]
    for name in names:
        lines.append(f"  - config_name: {name}")
        lines.append(f"    data_files: {name}.parquet")
    return "\n".join(lines) + "\n"


def gated_block(mode: str) -> str:
    if mode == "auto":
        return """extra_gated_heading: "Free 30% preview — instant access"
extra_gated_prompt: |
  This is a free, representative 30% sample of the full mixed-rights release.
  Approval is automatic: submit this form and the files unlock immediately.
  There is no purchase and no need to request the full dataset.

  The preview contains third-party metadata and retained upstream prose. Use it
  for non-commercial research or education, including model training. Do not
  redistribute the files or derivatives, and keep attribution to the named
  source owners. Attribution is not permission, and this gate is not a licence.
extra_gated_fields:
  Intended use:
    type: select
    options:
      - Research
      - Education
      - Model training
      - Evaluation
      - Other
  I agree to the access conditions: checkbox
extra_gated_button_content: "Get free access"
"""
    return """extra_gated_heading: "Request access to a mixed-rights dataset"
extra_gated_prompt: |
  This dataset contains third-party metadata and retained upstream prose.
  Access is for non-commercial research or education. By requesting access you
  agree not to redistribute the files or derivatives, to keep attribution to
  the named source owners, and to check LICENSE_AUDIT.md before any use.
  Attribution is not permission, and this gate is not a licence.
extra_gated_fields:
  Institution: text
  Intended use:
    type: select
    options:
      - Research
      - Education
      - Other
  I agree to the access conditions: checkbox
extra_gated_button_content: "Request access"
"""


TABLE_ORDER = (
    "anime", "characters", "staff", "episodes", "alt_titles",
    "relationships", "descriptions", "qa", "instructions", "rag_chunks",
    "entity_links", "franchises", "provenance", "license_tiers",
    "sources", "genres", "themes", "studios",
)
TABLE_LABELS = {
    "anime": "Anime works", "characters": "Characters",
    "staff": "Staff credits", "episodes": "Episodes",
    "alt_titles": "Alternative titles", "relationships": "Relationship edges",
    "descriptions": "Description rows", "qa": "Grounded QA pairs",
    "instructions": "Instruction examples", "rag_chunks": "RAG chunks",
    "entity_links": "Entity links", "franchises": "Franchise assignments",
    "provenance": "Provenance rows", "license_tiers": "License-tier rows",
    "sources": "Source registry", "genres": "Genres", "themes": "Themes",
    "studios": "Studios",
}
TIER_MEANING = {
    "cc0_only": "CC0-1.0; reuse freely",
    "permission_required": "AniList/Kitsu terms do not grant redistribution; written permission needed",
    "unresolved": "No permission basis identified; do not redistribute",
}


def build_card(repo_id: str, source: Path, gated: str) -> str:
    is_preview = (source / "preview_summary.json").exists()
    is_open = (source / "subset_summary.json").exists()
    s: dict = {}

    if is_preview:
        s = load_json(source / "preview_summary.json")
        version = s.get("version", "0.0.0")
        counts = s.get("counts", {})
        anime = s.get("anime", counts.get("anime", 0))
        population = s.get("population_anime", 0)
        rows = s.get("rows", sum(counts.values()))
        title = "Large Anime Text Dataset — 30% Free Preview"
        pretty = "Large Anime Text Dataset — 30% Free Preview"
        size = "100K<n<1M"
        licence = (
            "license: other\n"
            "license_name: mixed-rights-see-license-audit\n"
            f"license_link: https://huggingface.co/datasets/{repo_id}/blob/main/LICENSE_AUDIT.md"
        )
        tags = (
            "  - anime\n  - anime-dataset\n  - llm\n  - fine-tuning\n"
            "  - instruction-tuning\n  - question-answering\n  - rag\n"
            "  - retrieval-augmented-generation\n  - entity-linking\n"
            "  - knowledge-graph\n  - text-only\n  - japanese\n"
            "  - preview\n  - sample\n  - dataset"
        )
        works_badge = f"{anime:,}".replace(",", "%2C")
        badges = (
            f"![works](https://img.shields.io/badge/anime%20works-{works_badge}-0f766e?style=flat-square) "
            f"![rows](https://img.shields.io/badge/text%20rows-{rows/1e6:.2f}M-0f766e?style=flat-square) "
            "![sample](https://img.shields.io/badge/sample-30%25-0f766e?style=flat-square) "
            "![access](https://img.shields.io/badge/access-free%20instant-0f766e?style=flat-square) "
            "![license](https://img.shields.io/badge/license-mixed%20rights-b45309?style=flat-square)"
        )
        intro = (
            f"This is a **free, representative 30% sample** of the Large Anime Text "
            f"Dataset: **{anime:,} anime works** and **{rows:,} rows**, drawn from the "
            f"full {population:,}-work release. Sampling is stratified by "
            f"`(license_tier, split)` with seed {s.get('seed', 42)}, and every child "
            "row of a sampled work is kept, so the preview has the same tables, "
            "fields, split logic and licence mix as the full release."
        )
        access = f"""| Audience | This preview | Full release | CC0 subset |
| --- | --- | --- | --- |
| No Hugging Face account | card only | card only | **direct download** |
| Any Hugging Face account | **instant free access** | request → manual review | direct download |
| Use for model training | **allowed, non-commercial** | allowed after approval | allowed |
| Commercial use | upstream permission required | upstream permission required | CC0 metadata; CC-BY-4.0 project text |
| Redistribution | not permitted | not permitted | permitted with attribution |

There is **no purchase and no need to request the full dataset**. The preview is
free; approval is automatic. Gating controls access — it is not a licence from
AniList, Kitsu, Shikimori or Anime News Network."""
        gate_note = (
            "\n## Access\n\n"
            "Sign in to Hugging Face, select **Get free access**, and the files "
            "unlock immediately. The preview is free and automatically approved. "
            "Use is limited to non-commercial research or education, including "
            "model training; do not redistribute the files or derivatives.\n"
        )
        tier_section = (
            "## Licence mix in this preview\n\n"
            "The sample preserves the full release's obligations:\n\n"
            "| Tier | Works | What it means |\n| --- | ---: | --- |\n"
            + "\n".join(
                f"| `{t}` | {n:,} | {TIER_MEANING[t]} |"
                for t, n in sorted(s.get("tier_counts", {}).items()))
            + "\n\nSplits: "
            + ", ".join(f"`{k}` {v:,}" for k, v in sorted(s.get("split_counts", {}).items()))
            + " works. Only the `cc0_only` works are free of upstream obligations; "
            "the rest are included so the preview is representative, not because "
            "redistribution has been cleared.\n"
        )
        extra_format = ""
        ai_note = (
            "this preview is mixed-rights and gated; only the `cc0_only` works "
            f"inside it ({s.get('tier_counts', {}).get('cc0_only', 0):,}) are CC0."
        )
        omitted = ""
        citation_note = "30% free preview"
    elif is_open:
        s = load_json(source / "subset_summary.json")
        version = s.get("version", "0.0.0")
        counts = s.get("counts", {})
        anime = s.get("anime", counts.get("anime", 0))
        rows = s.get("rows", sum(counts.values()))
        title = "Large Anime Text Dataset — CC0 Subset"
        pretty = "Large Anime Text Dataset — CC0 Subset"
        size = "1K<n<10K"
        licence = "license: cc-by-4.0"
        tags = (
            "  - anime\n  - anime-dataset\n  - llm\n  - fine-tuning\n"
            "  - instruction-tuning\n  - question-answering\n  - rag\n"
            "  - retrieval-augmented-generation\n  - entity-linking\n"
            "  - text-only\n  - japanese\n  - cc0\n  - public-domain\n"
            "  - open-data\n  - dataset"
        )
        works_badge = f"{anime:,}".replace(",", "%2C")
        rows_badge = f"{rows:,}".replace(",", "%2C")
        badges = (
            f"![works](https://img.shields.io/badge/anime%20works-{works_badge}-0f766e?style=flat-square) "
            f"![rows](https://img.shields.io/badge/text%20rows-{rows_badge}-0f766e?style=flat-square) "
            "![access](https://img.shields.io/badge/access-public-0f766e?style=flat-square) "
            "![license](https://img.shields.io/badge/license-CC0%20%2B%20CC--BY--4.0-0f766e?style=flat-square)"
        )
        intro = (
            f"This is the **public, CC0-only subset**: **{anime:,} anime works** "
            "whose every contributing source is CC0-1.0. It contains no upstream "
            "synopsis, character biography or episode summary. Metadata is "
            "CC0-1.0; project-generated text is CC-BY-4.0. No gate, no account."
        )
        access = f"""| Audience | This CC0 subset | Full release | 30% preview |
| --- | --- | --- | --- |
| No Hugging Face account | **direct download** | card only | card only |
| Any Hugging Face account | direct download | request → manual review | instant free access |
| Use for model training | **allowed** | allowed after approval | allowed, non-commercial |
| Commercial use | **allowed** (CC0 metadata; CC-BY-4.0 project text) | upstream permission required | upstream permission required |
| Redistribution | **permitted with attribution** | not permitted | not permitted |

This is the only release in the family that is ungated. It is a small, clean
slice — not a 30% sample and not the full dataset."""
        gate_note = ""
        tier_section = (
            "## Licence coverage\n\n"
            f"All {anime:,} works are `cc0_only`. The subset contains **zero** "
            "upstream prose: no synopses, biographies, episode summaries or tag "
            "definitions. That is why it can be public.\n"
        )
        extra_format = ""
        ai_note = (
            "this subset is CC0 metadata plus CC-BY-4.0 project text; the full "
            "release is mixed-rights and gated."
        )
        omitted = ""
        if s.get("omitted_empty"):
            omitted = (
                "\nEmpty child tables are omitted from this subset: "
                + ", ".join(f"`{n}`" for n in s["omitted_empty"]) + ".\n"
            )
        citation_note = "CC0-only subset"
    else:
        s = load_json(ROOT / "reports" / "summary.json")
        e = s["entities"]
        version = s.get("version", "0.0.0")
        counts = {
            "anime": s["unique_titles"],
            "characters": e["characters"],
            "staff": e["staff"],
            "episodes": e["episodes"],
            "alt_titles": e["alt_titles"],
            "relationships": e["relationships"],
            "descriptions": e["descriptions"],
            "qa": e["qa_pairs"],
            "instructions": e["instructions"],
            "rag_chunks": e["rag_chunks"],
            "entity_links": s.get("entity_links", 0),
            "franchises": e.get("franchise_rows", 0),
            "provenance": e.get("provenance", 0),
            "license_tiers": e.get("license_tiers", 0),
            "sources": 6,
            "genres": e.get("genres", 0),
            "themes": e.get("themes", 0),
            "studios": e.get("studios", 0),
        }
        anime = s["unique_titles"]
        rows = sum(counts.values())
        title = "Large Anime Text Dataset"
        pretty = "Large Anime Text Dataset"
        size = "1M<n<10M"
        licence = (
            "license: other\n"
            "license_name: mixed-rights-see-license-audit\n"
            f"license_link: https://huggingface.co/datasets/{repo_id}/blob/main/LICENSE_AUDIT.md"
        )
        tags = (
            "  - anime\n  - anime-dataset\n  - llm\n  - llm-training\n"
            "  - fine-tuning\n  - instruction-tuning\n  - question-answering\n"
            "  - rag\n  - retrieval-augmented-generation\n  - entity-linking\n"
            "  - knowledge-graph\n  - text-only\n  - japanese\n  - nlp\n"
            "  - dataset"
        )
        works_badge = f"{anime:,}".replace(",", "%2C")
        badges = (
            f"![works](https://img.shields.io/badge/anime%20works-{works_badge}-0f766e?style=flat-square) "
            f"![rows](https://img.shields.io/badge/text%20rows-{rows/1e6:.2f}M-0f766e?style=flat-square) "
            "![format](https://img.shields.io/badge/format-JSONL%20%7C%20Parquet%20%7C%20CSV-4a5568?style=flat-square) "
            "![access](https://img.shields.io/badge/access-gated%20manual-b45309?style=flat-square) "
            "![license](https://img.shields.io/badge/license-mixed%20rights-b45309?style=flat-square)"
        )
        intro = (
            f"A text-only corpus of **{anime:,} anime works** and **{rows/1e6:.2f}M "
            "structured text rows**, built for LLM fine-tuning, instruction tuning, "
            "RAG, question answering, entity linking and recommendation. Every row "
            "carries provenance, confidence, split and a redistribution tier."
        )
        access = f"""| Audience | Full release | 30% preview | CC0 subset |
| --- | --- | --- | --- |
| No Hugging Face account | card only | card only | **direct download** |
| Any Hugging Face account | request → manual review | **instant free access** | direct download |
| Research or education | approved | approved | approved |
| Commercial use | upstream permission required | upstream permission required | CC0 metadata; CC-BY-4.0 project text |
| Redistribution | not permitted | not permitted | permitted with attribution |

The **30% preview is free and automatically approved** — no purchase and no need
to request this full release. The **CC0 subset is public**. This full release is
gated with manual approval for non-commercial research or education."""
        gate_note = (
            "\n## Access\n\n"
            "This repository is gated with **manual approval**. Sign in to Hugging "
            "Face, open this page and select **Request access**. Approval is for "
            "non-commercial research or education. Do not redistribute the files or "
            "derivatives.\n"
        )
        tier_section = (
            "## Licence tiers in this release\n\n"
            "| Tier | Works | What it means |\n| --- | ---: | --- |\n"
            + "\n".join(
                f"| `{t}` | {n:,} | {TIER_MEANING[t]} |"
                for t, n in sorted(s.get("license_tiers", {}).items()))
            + "\n\nEvery anime row is assigned the strictest tier implied by its "
            "sources (`unresolved` > `permission_required` > `cc0_only`). The tier "
            "describes this dataset's provenance obligation, not the copyright "
            "status of the underlying work.\n"
        )
        extra_format = " and SQLite in the full release"
        ai_note = (
            "the full release is mixed-rights and gated; only the `cc0_only` tier "
            f"({s.get('license_tiers', {}).get('cc0_only', 0):,} works) is CC0."
        )
        omitted = ""
        citation_note = "full mixed-rights release"

    table = "\n".join(
        f"| **{TABLE_LABELS[k]}** | {counts[k]:,} |"
        for k in TABLE_ORDER if counts.get(k)
    )
    configs = configs_block(source)
    gated_meta = gated_block(gated) if gated in ("auto", "manual") and not is_open else ""

    return f"""---
pretty_name: {pretty}
{licence}
language:
  - en
  - ja
tags:
{tags}
task_categories:
  - text-generation
  - question-answering
  - text-retrieval
size_categories:
  - {size}
{gated_meta}{configs}---

<div align="center">

<img src="https://muqeet-1138.github.io/anime-text-dataset/og.png" alt="Large Anime Text Dataset — 35,766 anime works and 2,436,445 structured text rows" width="100%">

# {title}

**{anime:,} anime works · {rows:,} text rows · text-only · JSONL / Parquet / CSV**

Built for LLM fine-tuning, instruction tuning, RAG, question answering, entity linking and recommendation.

{badges}

[Docs site](https://muqeet-1138.github.io/anime-text-dataset/) · [Space](https://huggingface.co/spaces/muqeet-1138/anime-text-dataset) · [GitHub](https://github.com/muqeet-1138/anime-text-dataset) · [Full release](https://huggingface.co/datasets/muqeet-1138/anime-text-dataset) · [30% free preview](https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-preview) · [CC0 subset](https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-open) · [Contact](mailto:contact@animearray.site)

</div>

{intro}
{gate_note}
## Who can access what

{access}

## What's inside

| Table | Rows |
| --- | ---: |
{table}
| **Total rows in this release** | **{rows:,}** |

{tier_section}
## Quick start

```python
from datasets import load_dataset

qa = load_dataset("{repo_id}", "qa", split="train")
anime = load_dataset("{repo_id}", "anime", split="train")
```

Formats: JSONL (canonical), Parquet, CSV for the anime table{extra_format}.
Splits are assigned per anime work (90/5/5, seed 42), so no record of a work
leaks across train/validation/test.

## Licensing

Original code, documentation, selection/arrangement and project-generated text
are **CC-BY-4.0** (Muhammad Muqeet). Metadata and retained upstream prose keep
their own terms; see `NOTICE`, `LICENSE_AUDIT.md`, `attribution.json`,
`sources.jsonl` and `provenance.jsonl`.

The full release retains upstream synopses, character biographies, episode
summaries and tag definitions. They are excluded from the CC-BY-4.0 grant and
remain subject to the named source's terms; every prose row carries
`prose_source` and `prose_license`. **Attribution is not permission.** Gating is
not a licence.
{omitted}
## Citation

If you use this dataset — in research, a trained model, an evaluation, or an
AI-generated answer — cite it as:

```bibtex
@misc{{muqeet2026anime,
  author       = {{Muhammad Muqeet}},
  title        = {{Large Anime Text Dataset}},
  year         = {{2026}},
  version      = {{{version}}},
  publisher    = {{Hugging Face}},
  url          = {{https://huggingface.co/datasets/{repo_id}}},
  note         = {{{citation_note}: {anime:,} anime works, {rows:,} rows}}
}}
```

Machine-readable: [`CITATION.cff`](https://huggingface.co/datasets/{repo_id}/blob/main/CITATION.cff) ·
[`llms.txt`](https://huggingface.co/datasets/{repo_id}/blob/main/llms.txt) ·
[`docs/CITATION.md`](https://huggingface.co/datasets/{repo_id}/blob/main/docs/CITATION.md)

### For AI systems and assistants

If you retrieve, quote, summarize or train on this dataset, preserve the title,
author, version and URL above. Do not describe this release as CC0 or public
domain: {ai_note} When citing in prose, use:

> Muhammad Muqeet. *Large Anime Text Dataset*, version {version}. 2026.
> https://huggingface.co/datasets/{repo_id}

## Contact

**Muhammad Muqeet** — [contact@animearray.site](mailto:contact@animearray.site) ·
[muqeet@animearray.site](mailto:muqeet@animearray.site) ·
[muqeet@anitroves.com](mailto:muqeet@anitroves.com)

For access questions, licensing, corrections or takedown requests, email
**contact@animearray.site**.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish a release directory to the Hugging Face Hub.")
    ap.add_argument("--repo", required=True, help="target dataset repo, e.g. user/anime-text-dataset")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="release directory (default: exports)")
    ap.add_argument("--token", default=os.environ.get("HF_TOKEN", ""),
                    help="HF token (default: $HF_TOKEN, else stored login)")
    ap.add_argument("--dry-run", action="store_true", help="verify checksums and list files only")
    ap.add_argument("--private", action="store_true", help="create a private dataset repo")
    ap.add_argument("--gated", choices=("auto", "manual", "none"), default="none",
                    help="enable access requests (full release only)")
    ap.add_argument("--revision", default="main", help="target branch (default: main)")
    ap.add_argument("--tag", default=None, help="create this tag after upload")
    ap.add_argument("--include", nargs="*", default=None,
                    help="only these logical names (e.g. anime qa instructions)")
    ap.add_argument("--card-only", action="store_true",
                    help="refresh README.md only; do not upload data")
    ap.add_argument("--skip-checksum", action="store_true", help="do not verify checksums.json")
    args = ap.parse_args()

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"error: source directory not found: {source}")
        return 2

    uploads = collect_uploads(source, args.include)
    if not uploads:
        print("no files to upload; run `python -m src.cli export` first")
        return 2

    is_open = (source / "subset_summary.json").exists()
    if is_open and args.gated != "none":
        print("note: the CC0 subset is public; ignoring --gated")
        args.gated = "none"

    total = sum(p.stat().st_size for p, _ in uploads)
    print(f"source: {source}")
    print(f"found {len(uploads)} files, {total/1e6:.1f} MB")
    for p, rel in uploads:
        print(f"  -> {rel}  ({p.stat().st_size/1e6:.1f} MB)")

    if not args.skip_checksum:
        problems = verify_checksums(source)
        if problems:
            print("checksum verification failed:")
            for p in problems[:10]:
                print(f"  ! {p}")
            return 1
        print("checksums: OK")

    if args.dry_run:
        print("dry-run: nothing uploaded")
        return 0

    try:
        from huggingface_hub import CommitOperationAdd, HfApi
    except ImportError:
        print('error: missing dependency; run: pip install "huggingface_hub[cli]"')
        return 2

    # An empty --token means "use the token saved by `huggingface-cli login`".
    api = HfApi(token=args.token or None)
    try:
        api.whoami()
    except Exception as exc:  # pragma: no cover - network
        print(f"error: not authenticated ({exc}); run `huggingface-cli login` or set HF_TOKEN")
        return 2

    try:
        info = api.create_repo(repo_id=args.repo, repo_type="dataset",
                               exist_ok=True, private=args.private)
        if args.gated in ("auto", "manual"):
            api.update_repo_settings(repo_id=args.repo, repo_type="dataset",
                                     gated=args.gated)
            print(f"gated: {args.gated}")
    except Exception as exc:  # pragma: no cover - network
        print(f"error creating repo: {exc}")
        return 1

    docs = [(p, rel) for p, rel in uploads if rel in {
        "LICENSE", "NOTICE", "LICENSE_AUDIT.md", "DATASET_CARD.md",
        "CITATION.cff", "llms.txt", "docs/LICENSE_NOTES.md",
        "docs/CITATION.md", "summary.json", "checksums.json"}]

    card = source / "README.md"
    card.write_text(build_card(args.repo, source, args.gated), encoding="utf-8")

    if args.card_only:
        try:
            api.create_commit(
                repo_id=args.repo,
                repo_type="dataset",
                revision=args.revision,
                commit_message="Refresh dataset card and citation docs",
                operations=[CommitOperationAdd(path_in_repo="README.md",
                                               path_or_fileobj=str(card))]
                + [CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(p))
                   for p, rel in docs],
            )
        except Exception as exc:  # pragma: no cover - network
            print(f"error uploading card: {exc}")
            return 1
        print(f"card: https://huggingface.co/datasets/{args.repo}")
        return 0

    print(f"uploading data to {info.repo_id} ({args.revision})…")
    try:
        api.upload_folder(
            folder_path=str(source),
            repo_id=args.repo,
            repo_type="dataset",
            revision=args.revision,
            commit_message=f"Upload Large Anime Text Dataset {args.tag or ''}".strip(),
        )
    except Exception as exc:  # pragma: no cover - network
        print(f"error uploading data: {exc}")
        return 1

    if docs:
        print(f"uploading {len(docs)} licence/provenance documents…")
        try:
            api.create_commit(
                repo_id=args.repo,
                repo_type="dataset",
                revision=args.revision,
                commit_message="Add licence, attribution and release summary",
                operations=[CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(p))
                            for p, rel in docs],
            )
        except Exception as exc:  # pragma: no cover - network
            print(f"error uploading documents: {exc}")
            return 1

    if args.tag:
        try:
            api.create_tag(args.repo, tag=args.tag, repo_type="dataset",
                           exist_ok=True)
            print(f"tag: {args.tag}")
        except Exception as exc:  # pragma: no cover - network
            print(f"warning: could not create tag: {exc}")

    print(f"done: https://huggingface.co/datasets/{args.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
