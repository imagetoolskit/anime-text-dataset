"""License tier classification and manifest generation.

Each anime row is assigned the strictest tier implied by the sources that
contributed to it. The tier names describe the actual obligation rather than
implying that attribution alone makes a record reusable:

  cc0_only             only CC0 (Wikidata) content contributed. Reusable with
                       no copyright obligation; attribution is courtesy.
  permission_required  AniList or Kitsu content contributed. Neither source's
                       terms grant redistribution of the content; permission is
                       required before publishing derived records.
  unresolved           Shikimori (terms not located) or ANN (copyrighted)
                       contributed. No permission basis; do not redistribute.

Writes:
  data/anime.db          license_tiers table (anime_id, tier, sources, reason)
  exports/license_tiers.jsonl
  exports/license_manifest.json
  exports/license_tier_<tier>.csv
  exports/license_commercial_clear.csv   (cc0_only)

This is an organizational aid, not legal advice.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SOURCE_TIER = {
    "anilist": "permission_required",
    "kitsu": "permission_required",
    "shikimori": "unresolved",
    "ann": "unresolved",
    "wikidata": "cc0_only",
}
PRECEDENCE = ["unresolved", "permission_required", "cc0_only"]

TIER_DEFINITIONS = {
    "cc0_only": {
        "obligation": "None. CC0 waives copyright; attribution is courtesy only.",
        "commercial_use": "allowed",
        "redistribution": "allowed",
        "sources": ["wikidata"],
    },
    "permission_required": {
        "obligation": "AniList and Kitsu terms allow API use but do not grant redistribution "
                      "of their content. Written permission from the provider and the "
                      "underlying rights holders is required before publishing records derived "
                      "from these fields.",
        "commercial_use": "not cleared",
        "redistribution": "not cleared",
        "sources": ["anilist", "kitsu"],
    },
    "unresolved": {
        "obligation": "Shikimori publishes no located license or terms for its data, and ANN "
                      "content is copyrighted. There is no permission basis for "
                      "redistribution.",
        "commercial_use": "not cleared",
        "redistribution": "not cleared",
        "sources": ["shikimori", "ann"],
    },
}


def get_sources(exports: Path | None = None) -> list[dict]:
    """Source registry, taken from the code that also writes sources.jsonl.

    Reading the previous export here would carry a one-release lag: tiering runs
    before export, so a stale file could label rows with superseded terms.
    """
    from src.pipeline.export import source_status
    return source_status()


def load_source_reasons(exports: Path | None = None) -> dict[str, str]:
    return {
        s["source_id"]: (f"{s['name']}: {s['license']} [{s['permission_status']}] "
                         f"(recorded {s['retrieval_date']})")
        for s in get_sources(exports)
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "anime.db"))
    ap.add_argument("--exports", default=str(ROOT / "exports"))
    ap.add_argument("--no-subsets", action="store_true")
    args = ap.parse_args(argv)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    reasons = load_source_reasons(Path(args.exports))

    agg: dict[int, dict] = {}
    for r in conn.execute(
        "select a.anime_id, a.title_canonical, a.title_english, s.source "
        "from anime a join anime_source s on s.anime_id=a.anime_id"
    ):
        tier = SOURCE_TIER.get(r["source"], "unresolved")
        idx = PRECEDENCE.index(tier)
        entry = agg.setdefault(r["anime_id"], {
            "tier_idx": 99, "tier": None, "sources": [],
            "title": r["title_canonical"] or r["title_english"],
        })
        if idx < entry["tier_idx"]:
            entry["tier_idx"] = idx
            entry["tier"] = tier
        if r["source"] not in entry["sources"]:
            entry["sources"].append(r["source"])

    # Any anime with no source links cannot be cleared either.
    for r in conn.execute("select anime_id, title_canonical, title_english from anime"):
        if r["anime_id"] not in agg:
            agg[r["anime_id"]] = {
                "tier_idx": 0, "tier": "unresolved", "sources": [],
                "title": r["title_canonical"] or r["title_english"],
            }

    rows = []
    by_tier = {t: 0 for t in PRECEDENCE}
    for aid, e in sorted(agg.items()):
        by_tier[e["tier"]] += 1
        rows.append({
            "anime_id": aid,
            "title": e["title"],
            "tier": e["tier"],
            "sources": sorted(e["sources"]),
            "reason": " | ".join(reasons[s] for s in sorted(e["sources"])) or "no source links",
        })

    exports = Path(args.exports)
    exports.mkdir(parents=True, exist_ok=True)
    # Drop tier subsets from an earlier naming scheme so a stale file can never
    # be mistaken for part of this release.
    for old in exports.glob("license_tier_*.csv"):
        if old.name not in {f"license_tier_{t}.csv" for t in PRECEDENCE}:
            old.unlink()
    with (exports / "license_tiers.jsonl").open("w", encoding="utf-8") as f:
        for o in rows:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

    conn.execute("CREATE TABLE IF NOT EXISTS license_tiers ("
                 "anime_id INTEGER PRIMARY KEY, tier TEXT NOT NULL, "
                 "sources TEXT, reason TEXT)")
    conn.execute("DELETE FROM license_tiers")
    conn.executemany(
        "INSERT INTO license_tiers(anime_id, tier, sources, reason) VALUES(?,?,?,?)",
        [(o["anime_id"], o["tier"], json.dumps(o["sources"]), o["reason"]) for o in rows])
    conn.commit()

    commercial_clear = by_tier["cc0_only"]
    manifest = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                        .isoformat(timespec="seconds"),
        "scope": "one tier per anime row; the strictest contributing source wins",
        "precedence": PRECEDENCE,
        "tier_definitions": TIER_DEFINITIONS,
        "counts": {
            "anime_total": len(rows),
            **by_tier,
            "commercial_clear": commercial_clear,
            "commercial_clear_share": round(commercial_clear / max(len(rows), 1), 4),
        },
        "source_status": get_sources(exports),
        "content_policy": {
            "upstream_prose": "removed",
            "removed_fields": [
                "anime.synopsis",
                "anime.synopsis_source",
                "characters.description",
                "episodes.synopsis",
                "themes.description",
                "genres.description",
                "descriptions.kind=source_synopsis",
                "rag_chunks.kind=source_synopsis",
                "qa_pairs.qtype=synopsis",
            ],
            "shipped_text": "factual fields, short names and titles, and project-generated text",
            "reason": (
                "Upstream synopses and character bios are third-party expression. No source "
                "terms grant redistribution, and a close paraphrase would still be a "
                "derivative work, so the fields are dropped instead of rewritten."
            ),
            "project_text_license": "CC-BY-4.0, Muhammad Muqeet",
            "not_shipped": ["data/anime.db", "data/cache", "raw_payload payload column"],
        },
        "known_gaps": [
            "Shikimori publishes no located license or terms for API data.",
            "AniList terms do not grant redistribution and prohibit hoarding or mass collection; "
            "permission is required.",
            "Kitsu's terms do not grant redistribution of API data; permission is required.",
            "ANN sample pages are retained in raw storage but linked to zero exported rows.",
            "MAL/Jikan is unreachable from the collection environment and was excluded.",
            "Tiers describe the dataset's own provenance, not the copyright status of the "
            "underlying anime works, which remain with their rights holders.",
        ],
        "subsets": [
            "license_tier_cc0_only.csv",
            "license_tier_permission_required.csv",
            "license_tier_unresolved.csv",
            "license_commercial_clear.csv",
        ],
        "disclaimer": "Organizational aid, not legal advice. Verify upstream terms before use.",
    }
    (exports / "license_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.no_subsets:
        ids_by_tier: dict[str, list[int]] = {t: [] for t in PRECEDENCE}
        for o in rows:
            ids_by_tier[o["tier"]].append(o["anime_id"])
        for tier, ids in ids_by_tier.items():
            with (exports / f"license_tier_{tier}.csv").open("w", encoding="utf-8",
                                                             newline="") as f:
                w = csv.writer(f)
                w.writerow(["anime_id"])
                for i in ids:
                    w.writerow([i])
        with (exports / "license_commercial_clear.csv").open("w", encoding="utf-8",
                                                            newline="") as f:
            w = csv.writer(f)
            w.writerow(["anime_id", "tier"])
            for o in rows:
                if o["tier"] == "cc0_only":
                    w.writerow([o["anime_id"], o["tier"]])

    print(json.dumps({"rows": len(rows), "by_tier": by_tier,
                      "commercial_clear": commercial_clear}), file=sys.stdout)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
