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
             "CITATION.cff")


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
    summary = source / "subset_summary.json"
    if not summary.exists():
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


def gated_block() -> str:
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


def build_card(repo_id: str, source: Path, gated: str) -> str:
    is_open = (source / "subset_summary.json").exists()
    if is_open:
        s = load_json(source / "subset_summary.json")
        version = s.get("version", "0.0.0")
        counts = s.get("counts", {})
        anime = s.get("anime", counts.get("anime", 0))
        rows = s.get("rows", 0)
        title = f"Large Anime Text Dataset — CC0-only subset (v{version})"
        size = "1K<n<10K"
        licence = "license: cc-by-4.0"
        tags = ("  - anime\n  - llm\n  - qa\n  - instruction-tuning\n"
                "  - rag\n  - cc0\n  - text")
    else:
        s = load_json(ROOT / "reports" / "summary.json")
        e = s["entities"]
        version = s.get("version", "0.0.0")
        counts = {
            "anime": s["unique_titles"], "characters": e["characters"],
            "staff": e["staff"], "episodes": e["episodes"],
            "descriptions": e["descriptions"], "qa": e["qa_pairs"],
            "instructions": e["instructions"], "rag_chunks": e["rag_chunks"],
            "alt_titles": e["alt_titles"], "relationships": e["relationships"],
        }
        anime = s["unique_titles"]
        rows = sum(counts.values())
        title = f"Large Anime Text Dataset (v{version})"
        size = "1M<n<10M"
        licence = (
            "license: other\n"
            "license_name: mixed-see-license-audit\n"
            f"license_link: https://huggingface.co/datasets/{repo_id}/blob/main/LICENSE_AUDIT.md"
        )
        tags = ("  - anime\n  - llm\n  - fine-tuning\n  - qa\n"
                "  - instruction-tuning\n  - rag\n  - entity-linking\n  - text")

    label = {
        "anime": "Anime works", "characters": "Characters",
        "staff": "Staff credits", "episodes": "Episodes",
        "descriptions": "Description rows", "qa": "QA pairs",
        "instructions": "Instruction examples", "rag_chunks": "RAG chunks",
        "alt_titles": "Alternative titles", "relationships": "Relation edges",
        "entity_links": "Entity links", "franchises": "Franchise rows",
        "provenance": "Provenance rows", "sources": "Source records",
        "license_tiers": "License-tier rows",
    }
    table = "\n".join(
        f"| **{label.get(k, k)}** | {v:,} |"
        for k, v in counts.items() if v
    )

    if is_open:
        intro = (
            "This is the **public, CC0-only subset**: works whose every "
            "contributing source is CC0-1.0. It contains no upstream synopsis, "
            "character biography or episode summary. Project-generated text is "
            "CC-BY-4.0; metadata is CC0-1.0."
        )
        gate_note = ""
    else:
        intro = (
            "Text-only dataset for LLM fine-tuning, RAG, QA, entity linking and "
            "recommendation. This is the **full mixed-rights release**; access "
            "is gated and manual. Only 969 of 35,766 works (2.7%) are tiered "
            "`cc0_only`; the rest carry upstream obligations."
        )
        gate_note = (
            "\n## Access\n\n"
            "This repository is gated. Run `huggingface-cli login`, then request "
            "access on the Hub. Access is for non-commercial research or "
            "education; do not redistribute the files or derivatives.\n"
        )

    configs = configs_block(source)
    gated_meta = gated_block() if gated in ("auto", "manual") and not is_open else ""
    omitted = ""
    if is_open and s.get("omitted_empty"):
        omitted = ("\nEmpty child tables are omitted from this subset: "
                   + ", ".join(f"`{n}`" for n in s["omitted_empty"]) + ".\n")

    return f"""---
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

# {title}

{intro}

| Section | Rows |
| --- | ---: |
{table}
| **Total rows in this release** | {rows:,} |

Splits are assigned per anime work (90/5/5, seed 42), so no record of a work
leaks across train/validation/test. Formats: JSONL (canonical), Parquet, CSV
for the anime table, and SQLite in the full release.
{gate_note}
## Getting started

```python
from datasets import load_dataset

anime = load_dataset("{repo_id}", "anime", split="train")
qa = load_dataset("{repo_id}", "qa", split="train")
```

## License & attribution

Original code, documentation, selection/arrangement and project-generated text
are CC-BY-4.0 (Muhammad Muqeet). Metadata and retained upstream prose keep
their own terms; see `NOTICE`, `LICENSE_AUDIT.md`, `attribution.json`,
`sources.jsonl` and `provenance.jsonl`.

The full release retains upstream synopses, character biographies, episode
summaries and tag definitions. They are excluded from the CC-BY-4.0 grant and
remain subject to the named source's terms; every prose row carries
`prose_source` and `prose_license`. Attribution is not permission.
{omitted}
## Citation

```bibtex
@misc{{large-anime-text-dataset,
  author = "Muhammad Muqeet",
  title  = "Large Anime Text Dataset v{version}",
  year   = "2026",
  url    = "https://huggingface.co/datasets/{repo_id}"
}}
```
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

    card = source / "README.md"
    card.write_text(build_card(args.repo, source, args.gated), encoding="utf-8")

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

    docs = [(p, rel) for p, rel in uploads if rel in {
        "LICENSE", "NOTICE", "LICENSE_AUDIT.md", "DATASET_CARD.md",
        "CITATION.cff", "docs/LICENSE_NOTES.md", "summary.json"}]
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
