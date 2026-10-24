"""Keep every number in the docs and site pages in sync with the release.

Two mechanisms, both driven by `reports/summary.json` (itself generated from the
database by `python -m src.cli report`):

1. **Blocks** between `<!-- counts:start -->` and `<!-- counts:end -->` in the
   Markdown docs are regenerated wholesale. Editing them by hand is pointless:
   the next run overwrites them.
2. **Tokens** of the form `{{n:metric}}` and `{{v:version}}` in the HTML source
   pages under `docs_src/` are substituted when the pages are rendered into
   `docs/`. The source keeps the tokens, so every run can refresh the numbers
   and `--check` stays meaningful after the first render.

Prose outside the markers and tokens is never touched.

Usage:
    python scripts/sync_docs.py            # rewrite blocks, render docs_src -> docs
    python scripts/sync_docs.py --check    # exit 1 if anything is out of date
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- counts:start -->"
END = "<!-- counts:end -->"

BLOCK_DOCS = {
    "README.md": "readme",
    "DATASET_CARD.md": "card",
    "docs/TRAINING.md": "training",
}
TOKEN_GLOB = "docs_src/*.html"
HTML_OUT = ROOT / "docs"
TOKEN_RE = re.compile(r"\{\{([nvr]):([a-z0-9_]+)\}\}")


def fmt(n: int) -> str:
    return f"{n:,}"


def metrics(summary: dict) -> dict[str, str]:
    """Flat, string-valued lookup used by both renderers."""
    e = summary["entities"]
    cov = summary["field_coverage"]
    splits = summary["splits"]
    by_source = summary.get("by_source", {})
    raw = summary.get("raw_payloads", {})
    m = {
        "version": summary.get("version", ""),
        "unique_titles": fmt(summary["unique_titles"]),
        "characters": fmt(e["characters"]),
        "staff": fmt(e["staff"]),
        "episodes": fmt(e["episodes"]),
        "relationships": fmt(e["relationships"]),
        "alt_titles": fmt(e["alt_titles"]),
        "descriptions": fmt(e["descriptions"]),
        "qa_pairs": fmt(e["qa_pairs"]),
        "instructions": fmt(e["instructions"]),
        "rag_chunks": fmt(e["rag_chunks"]),
        "license_tiers": fmt(e["license_tiers"]),
        "provenance": fmt(e.get("provenance", 0)),
        "franchises": fmt(e["franchises"]),
        "franchise_rows": fmt(e["franchise_rows"]),
        "studios": fmt(e["studios"]),
        "genres": fmt(e["genres"]),
        "themes": fmt(e["themes"]),
        "entity_links": fmt(summary.get("entity_links", sum(by_source.values()))),
        "split_train": fmt(splits.get("train", 0)),
        "split_val": fmt(splits.get("val", 0)),
        "split_test": fmt(splits.get("test", 0)),
        "anilist_full": fmt(raw.get("anilist:media_full", 0)),
    }
    for source in ("anilist", "kitsu", "shikimori", "wikidata", "ann"):
        m[f"src_{source}"] = fmt(by_source.get(source, 0))
    m["src_shikimori_detail"] = fmt(raw.get("shikimori:detail", 0))
    m["src_shikimori_roles"] = fmt(raw.get("shikimori:roles", 0))
    m["src_kitsu_episodes"] = fmt(raw.get("kitsu:episodes", 0))
    for key, value in raw.items():
        m["raw_" + re.sub(r"[^a-z0-9]+", "_", key.lower())] = fmt(value)
    m["episodes_compact"] = f"{e['episodes'] // 1000}k"
    m["episode_list_share"] = f"{summary['episode_list_share']:.0%}"
    for label, entry in cov.items():
        key = "cov_" + re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        m[key] = f"{entry['share']:.0%}"
        # Two-decimal form, for the JavaScript snapshot embedded in explore.html.
        m["covraw_" + key[4:]] = f"{entry['share'] * 100:.2f}"
    return m


def build_block(summary: dict, kind: str) -> str:
    e = summary["entities"]
    cov = summary["field_coverage"]
    splits = summary["splits"]
    m = metrics(summary)

    def share(field: str) -> str:
        return f"{cov[field]['share']:.0%}"

    if kind == "readme":
        lines = [
            "| Metric | Value |",
            "| --- | --- |",
            f"| Unique anime works with at least one title | **{m['unique_titles']}** |",
            f"| Characters | {m['characters']} |",
            f"| Staff credits | {m['staff']} |",
            f"| Episodes | {m['episodes']} |",
            f"| Alternative titles | {m['alt_titles']} |",
            f"| Relationship edges | {m['relationships']} |",
            f"| Franchise clusters | {m['franchises']} |",
            f"| Record summaries | {m['descriptions']} |",
            f"| Question/answer pairs | {m['qa_pairs']} |",
            f"| Instruction-tuning examples | {m['instructions']} |",
            f"| RAG chunks | {m['rag_chunks']} |",
            f"| Split: train / val / test | {m['split_train']} / "
            f"{m['split_val']} / {m['split_test']} |",
            "",
            "Coverage of the anime table (share of rows carrying a value):",
            "",
            "| Field | Coverage |",
            "| --- | ---: |",
            f"| Year | {share('year')} |",
            f"| Episode count | {share('episodes (count)')} |",
            f"| Per-episode records | {summary['episode_list_share']:.0%} |",
            f"| Studios | {share('studios')} |",
            f"| Genres | {share('genres')} |",
            f"| Characters | {share('characters')} |",
            f"| Voice actors | {share('voice actors')} |",
            f"| Staff credits | {share('staff credits')} |",
            f"| Relationships | {share('relationships')} |",
        ]
        return "\n".join(lines)

    if kind == "card":
        lines = [
            "| Field | Value |",
            "| --- | --- |",
            f"| Unique anime works | **{m['unique_titles']}** |",
            f"| Characters / staff credits | {m['characters']} / {m['staff']} |",
            f"| Episodes | {m['episodes']} |",
            f"| QA pairs / instructions / RAG chunks | {m['qa_pairs']} / "
            f"{m['instructions']} / {m['rag_chunks']} |",
            f"| Alternative titles / relationship edges | {m['alt_titles']} / "
            f"{m['relationships']} |",
            f"| Descriptions | {m['descriptions']} |",
            f"| License tiers | {m['license_tiers']} |",
            f"| Split | train {m['split_train']} / val {m['split_val']} / "
            f"test {m['split_test']} |",
            "| Formats | JSONL (canonical), SQLite, Parquet, CSV |",
        ]
        return "\n".join(lines)

    if kind == "training":
        lines = [
            "| Training input | File | Rows | Best used for |",
            "| --- | --- | ---: | --- |",
            f"| QA pairs (incl. deliberate abstentions) | `exports/qa.jsonl` | {m['qa_pairs']} | SFT, RAG readers, preference tuning |",
            f"| Instruction examples | `exports/instructions.jsonl` | {m['instructions']} | SFT, LoRA/QLoRA, chat models |",
            f"| Grounded descriptive text | `exports/descriptions.jsonl` | {m['descriptions']} | continual pretraining |",
            f"| RAG chunks + `source_refs` | `exports/rag_chunks.jsonl` | {m['rag_chunks']} | retrieval, embeddings, RAG |",
            f"| Canonical records | `exports/anime.jsonl` | {m['unique_titles']} | classification, ranking, KG |",
            f"| Characters | `exports/characters.jsonl` | {m['characters']} | character extraction, KG |",
            f"| Staff credits | `exports/staff.jsonl` | {m['staff']} | crew extraction, KG |",
            f"| Episodes | `exports/episodes.jsonl` | {m['episodes']} | episode QA (Kitsu-linked works only) |",
            f"| Relation edges | `exports/relationships.jsonl` | {m['relationships']} | relation extraction, KG |",
            f"| Alternative titles | `exports/alt_titles.jsonl` | {m['alt_titles']} | title normalization, alias resolution |",
            f"| Per-anime license tiers | `exports/license_tiers.jsonl` | {m['license_tiers']} | filtering before publication |",
            "| Split field on every record | every table | — | leakage-free train/val/test |",
        ]
        return "\n".join(lines)

    raise ValueError(kind)


def replace_block(text: str, block: str) -> str:
    i = text.find(START)
    j = text.find(END)
    if i < 0 or j < 0:
        raise SystemExit(f"missing {START} / {END} markers")
    return text[: i + len(START)] + "\n" + block + "\n" + text[j:]


def render_tokens(text: str, lookup: dict[str, str]) -> str:
    missing: list[str] = []

    def sub(match: re.Match) -> str:
        kind, key = match.group(1), match.group(2)
        if kind == "v":
            return lookup.get("version", "")
        if key not in lookup:
            missing.append(key)
            return match.group(0)
        # `r` is the raw numeric form used inside JavaScript literals, where a
        # thousands separator would be a syntax error.
        return lookup[key].replace(",", "") if kind == "r" else lookup[key]

    out = TOKEN_RE.sub(sub, text)
    if missing:
        raise SystemExit(f"unknown metric(s) in token: {sorted(set(missing))}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    summary_path = ROOT / "reports" / "summary.json"
    if not summary_path.exists():
        print("reports/summary.json missing: run `python -m src.cli report` first",
              file=sys.stderr)
        return 2
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    missing = [k for k in ("entities", "field_coverage", "splits", "unique_titles")
               if k not in summary]
    if missing:
        print(f"reports/summary.json is from an older release (missing {', '.join(missing)}); "
              "run `python -m src.cli report` first", file=sys.stderr)
        return 2
    lookup = metrics(summary)

    stale: list[str] = []
    for name, kind in BLOCK_DOCS.items():
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        updated = replace_block(text, build_block(summary, kind))
        if updated != text:
            stale.append(name)
            if not args.check:
                path.write_text(updated, encoding="utf-8")

    for src in sorted(ROOT.glob(TOKEN_GLOB)):
        text = src.read_text(encoding="utf-8")
        updated = render_tokens(text, lookup)
        out_path = HTML_OUT / src.name
        current = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if updated != current:
            stale.append(str(out_path.relative_to(ROOT)).replace("\\", "/"))
            if not args.check:
                out_path.write_text(updated, encoding="utf-8")

    if args.check:
        if stale:
            print(f"out of date: {', '.join(stale)}", file=sys.stderr)
            return 1
        print("docs counts up to date")
        return 0
    print(f"updated: {', '.join(stale) if stale else 'nothing to change'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
