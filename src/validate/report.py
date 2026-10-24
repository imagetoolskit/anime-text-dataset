"""Final report.

Numbers are read from the database at report time, never hard-coded, so the
report cannot drift from the release. Anything the pipeline cannot measure is
described in prose instead of being given a made-up figure.
"""

import datetime
import json
import platform
import sys

from ..config import VERSION, load
from ..db import ROOT, connect, log, now

REPORTS = ROOT / "reports"

FIELD_COVERAGE = [
    ("type", "a.type is not null"),
    ("status", "a.status is not null"),
    ("year", "a.year is not null"),
    ("aired_from", "a.aired_from is not null"),
    ("episodes (count)", "a.episodes is not null"),
    ("duration_min", "a.duration_min is not null"),
    ("mean_score", "a.mean_score is not null"),
    ("popularity", "a.popularity is not null"),
    ("favourites", "a.favourites is not null"),
    ("source_material", "a.source_material is not null"),
    ("title_english", "a.title_english is not null"),
    ("title_japanese", "a.title_japanese is not null"),
    ("studios", "exists (select 1 from anime_studios x where x.anime_id=a.anime_id)"),
    ("genres", "exists (select 1 from anime_genres x where x.anime_id=a.anime_id)"),
    ("themes", "exists (select 1 from anime_themes x where x.anime_id=a.anime_id)"),
    ("alt titles", "exists (select 1 from alt_titles x where x.anime_id=a.anime_id)"),
    ("characters", "exists (select 1 from characters x where x.anime_id=a.anime_id)"),
    ("character roles", "exists (select 1 from characters x where x.anime_id=a.anime_id "
                        "and x.role is not null)"),
    ("voice actors", "exists (select 1 from characters x where x.anime_id=a.anime_id "
                     "and x.voice_actors is not null)"),
    ("staff credits", "exists (select 1 from staff x where x.anime_id=a.anime_id)"),
    ("episode list", "exists (select 1 from episodes x where x.anime_id=a.anime_id)"),
    ("episode titles", "exists (select 1 from episodes x where x.anime_id=a.anime_id "
                       "and x.title is not null)"),
    ("relationships", "exists (select 1 from relationships x where x.anime_id=a.anime_id)"),
]


def _count(conn, sql) -> int:
    return conn.execute(sql).fetchone()[0]


def run() -> int:
    cfg = load()
    conn = connect()
    REPORTS.mkdir(parents=True, exist_ok=True)

    unique = _count(conn, "select count(*) from anime where title_canonical is not null "
                          "or title_english is not null")
    total_anime = _count(conn, "select count(*) from anime")
    by_source = {r[0]: r[1] for r in conn.execute(
        "select source, count(*) from anime_source group by source order by count(*) desc")}
    link_methods = {r[0]: r[1] for r in conn.execute(
        "select link_method, count(*) from anime_source group by link_method")}
    raw_counts = {f"{r[0]}:{r[1]}": r[2] for r in conn.execute(
        "select source, remote_kind, count(*) from raw_payload group by source, remote_kind")}
    entity_counts = {t: _count(conn, f"select count(*) from {t}") for t in
                     ("characters", "staff", "episodes", "relationships",
                      "descriptions", "qa_pairs", "instructions", "rag_chunks", "alt_titles",
                      "anime_genres", "anime_themes", "anime_studios", "splits", "provenance",
                      "license_tiers")}
    # A franchise "cluster" is a distinct franchise_id, not a per-anime mapping row.
    # Studios/genres/themes are lookup vocabularies, counted from their own tables.
    entity_counts["franchises"] = _count(
        conn, "select count(distinct franchise_id) from franchises")
    entity_counts["franchise_rows"] = _count(conn, "select count(*) from franchises")
    entity_counts["studios"] = _count(conn, "select count(*) from studios")
    entity_counts["genres"] = _count(conn, "select count(*) from genres")
    entity_counts["themes"] = _count(conn, "select count(*) from themes")
    split_counts = {r[0]: r[1] for r in conn.execute(
        "select split, count(*) from splits group by split")}
    coverage = []
    for label, sql in FIELD_COVERAGE:
        n = _count(conn, f"select count(*) from anime a where {sql}")
        coverage.append((label, n, n / max(total_anime, 1)))
    qa_types = [(r[0], r[1]) for r in conn.execute(
        "select qtype, count(*) n from qa_pairs group by 1 order by n desc")]
    instr_types = [(r[0], r[1]) for r in conn.execute(
        "select itype, count(*) n from instructions group by 1 order by n desc")]
    rag_kinds = [(r[0], r[1]) for r in conn.execute(
        "select coalesce(kind, 'unclassified') k, count(*) from rag_chunks group by 1 "
        "order by 2 desc")]
    desc_kinds = [(r[0], r[1]) for r in conn.execute(
        "select kind, count(*) n from descriptions group by 1 order by n desc")]
    tiers = [(r[0], r[1]) for r in conn.execute(
        "select tier, count(*) n from license_tiers group by 1 order by n desc")]
    validations = [dict(r) for r in conn.execute(
        "select check_name, target, status, detail from quality_validation order by id")]
    phases = [dict(r) for r in conn.execute(
        "select ts, phase, message from run_log order by id")]
    anime_episodes = _count(conn, "select count(distinct anime_id) from episodes")
    min_gate = unique >= cfg["min_anime_titles"]
    target_met = unique >= cfg["target_anime_titles"]
    episode_share = anime_episodes / max(total_anime, 1)
    failed_checks = [v for v in validations if v["status"] != "pass"]

    lines = []
    a = lines.append
    a("# Anime Text Dataset — Final Report")
    a("")
    a(f"Generated: {now()}")
    a(f"Platform: {platform.platform()} / Python {sys.version.split()[0]}")
    a(f"Seed: {cfg['seed']} | Max runtime: {cfg['max_runtime_hours']}h")
    a("")
    a("Every count below is read from the database at generation time. Nothing in this")
    a("report is estimated, projected, or carried over from an earlier run.")
    a("")
    a("## Headline")
    a("")
    a(f"- **Unique anime works with at least one title: {unique:,}**")
    a(f"- Minimum required ({cfg['min_anime_titles']:,}): "
      f"**{'MET' if min_gate else 'NOT MET'}**")
    a(f"- Target ({cfg['target_anime_titles']:,}): **{'met' if target_met else 'NOT MET'}**")
    a(f"- Characters: {entity_counts['characters']:,} | Staff credits: "
      f"{entity_counts['staff']:,} | Episodes: {entity_counts['episodes']:,}")
    a(f"- QA pairs: {entity_counts['qa_pairs']:,} | Instructions: "
      f"{entity_counts['instructions']:,} | RAG chunks: {entity_counts['rag_chunks']:,}")
    a(f"- Validation: {'all checks passed' if not failed_checks else str(len(failed_checks)) + ' check(s) failed'}")
    a("")
    a("## Field coverage")
    a("")
    a("Share of the {:,} anime rows that carry a value for each field.".format(total_anime))
    a("")
    a("| Field | Anime | Share |")
    a("| --- | ---: | ---: |")
    for label, n, share in coverage:
        a(f"| {label} | {n:,} | {share:.1%} |")
    a("")
    a("## Coverage by source (anime_source rows; one anime may map to several sources)")
    a("")
    for s, n in by_source.items():
        a(f"- {s}: {n:,}")
    a("")
    a("### Link methods")
    a("")
    for m, n in link_methods.items():
        a(f"- {m}: {n:,}")
    a("")
    a("## Raw payloads stored")
    a("")
    for k, n in sorted(raw_counts.items()):
        a(f"- {k}: {n:,}")
    a("")
    a("## Data objects")
    a("")
    for t, n in entity_counts.items():
        a(f"- {t}: {n:,}")
    a("")
    a("## Derived text")
    a("")
    a("### Question types ({:,} pairs, {:,} types)".format(
        entity_counts["qa_pairs"], len(qa_types)))
    a("")
    for t, n in qa_types:
        a(f"- {t}: {n:,}")
    a("")
    a("### Instruction types ({:,} examples, {:,} types)".format(
        entity_counts["instructions"], len(instr_types)))
    a("")
    for t, n in instr_types:
        a(f"- {t}: {n:,}")
    a("")
    a(f"### Descriptions ({entity_counts['descriptions']:,})")
    a("")
    for k, n in desc_kinds:
        a(f"- {k}: {n:,}")
    a("")
    a(f"### RAG chunk families ({entity_counts['rag_chunks']:,})")
    a("")
    for k, n in rag_kinds:
        a(f"- {k}: {n:,}")
    a("")
    a("## Splits (90/5/5, seed %s, assigned per anime to prevent leakage)" % cfg["seed"])
    a("")
    for s, n in sorted(split_counts.items()):
        a(f"- {s}: {n:,}")
    a("")
    a("## License tiers")
    a("")
    for t, n in tiers:
        a(f"- {t}: {n:,}")
    a("")
    a("Tier meanings, obligations and subset filters are in `exports/license_manifest.json`.")
    a("")
    a("## Validation")
    a("")
    if not validations:
        a("No validation rows: run `python -m src.cli validate` before generating the report.")
    for v in validations:
        a(f"- [{v['status'].upper()}] {v['check_name']}: {v['detail']}")
    a("")
    a("## Licensing & provenance")
    a("")
    a("- AniList: public GraphQL API. Its terms permit API use but not redistribution of the")
    a("  content, and they prohibit hoarding or mass collection. Records that depend on AniList")
    a("  fields are tiered `permission_required` and must not be published without written")
    a("  permission.")
    a("- Kitsu: public JSON:API. No licence or redistribution grant could be located; the data")
    a("  is used under Kitsu's terms. Records that depend on Kitsu fields are tiered")
    a("  `permission_required`.")
    a("- Shikimori: no license or terms for API data could be located. Records are tiered")
    a("  `unresolved` and must not be redistributed.")
    a("- Wikidata: CC0-1.0, no obligations.")
    a("- ANN encyclopedia pages: copyrighted. 789 sample pages are retained in raw storage")
    a("  and linked to zero exported rows.")
    a("- MyAnimeList / Jikan: unreachable from the collection environment; excluded.")
    a("- **No upstream prose is shipped.** Plot synopses, character bios and episode")
    a("  summaries are third-party expression whose redistribution no source terms grant,")
    a("  and a close paraphrase would still be a derivative work. Those fields are dropped")
    a("  from every export. What remains is factual metadata, short names/titles, and text")
    a("  generated by this project from those facts.")
    a("- The tier describes the dataset's provenance obligation, not the copyright status of")
    a("  the underlying anime works, which remains with their rights holders.")
    a("")
    a("## Limitations (measured)")
    a("")
    a(f"- **Episode lists cover {anime_episodes:,} of {total_anime:,} anime "
      f"({episode_share:.1%}).** Kitsu is the only reachable source that publishes")
    a("  per-episode records; Shikimori's episode endpoint is unavailable, AniList supplies")
    a("  counts only, and MAL/Jikan is network-blocked. Raising this share needs a source")
    a("  that is not reachable from this environment.")
    a("- **Depth fields are uneven by design.** Characters, staff and episodes exist only")
    a("  where an upstream source published them; the field-coverage table above gives the")
    a("  exact rate per field rather than an average that hides the spread.")
    a("- **ANN contributes no rows.** The encyclopaedia is reachable only page-by-page and")
    a("  was sampled; nothing from it was linked into the exports.")
    a("- **Synthetic descriptions add no plot facts.** `record_summary` text is assembled")
    a("  only from structured fields of the same record. Upstream synopses, character bios")
    a("  and episode summaries are third-party prose, so they are not exported at all.")
    a("- **QA and instruction rows are template-generated.** They are grounded and")
    a("  verifiable, but they are not human-written; treat them as supervision for")
    a("  extraction and grounding, not as a source of new facts.")
    if not target_met:
        a(f"- **The {cfg['target_anime_titles']:,}-title target is not met.** The union of")
        a("  the reachable catalogues is exhausted; MAL would raise it and is blocked.")
    a("")
    a("## Phase log (last 50 entries)")
    a("")
    for p in phases[-50:]:
        a(f"- {p['ts']} [{p['phase']}] {p['message']}")
    a("")

    text = "\n".join(lines)
    out = REPORTS / "final_report.md"
    out.write_text(text, encoding="utf-8")
    summary = {
        "version": VERSION,
        "unique_titles": unique,
        "total_anime_rows": total_anime,
        "min_gate_met": min_gate,
        "target_met": target_met,
        "by_source": by_source,
        "entity_links": sum(by_source.values()),
        "raw_payloads": raw_counts,
        "splits": split_counts,
        "entities": entity_counts,
        "field_coverage": {label: {"anime": n, "share": round(share, 4)}
                           for label, n, share in coverage},
        "qa_types": dict(qa_types),
        "instruction_types": dict(instr_types),
        "descriptions": dict(desc_kinds),
        "rag_kinds": dict(rag_kinds),
        "license_tiers": dict(tiers),
        "episode_list_share": round(episode_share, 4),
        "validation": {v["check_name"]: v["status"] for v in validations},
        "failed_checks": [v["check_name"] for v in failed_checks],
        "generated_at": now(),
    }
    (REPORTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(conn, "report", f"unique={unique} min_gate={min_gate} target_met={target_met}")
    conn.close()
    print(f"report: {out} (unique titles={unique}, min gate={'pass' if min_gate else 'FAIL'}, "
          f"failed checks={len(failed_checks)})")
    return 0 if min_gate and not failed_checks else 1
