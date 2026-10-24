"""Release export.

Every per-anime table carries `split` and `license_tier` so a consumer can
filter a training set without joining anything. JSON fields are emitted as
arrays, not encoded strings.
"""

import csv
import json
import pathlib

from ..config import load
from ..db import ROOT, connect, cp_set, log, now

EXPORT_DIR = ROOT / "exports"

CHILD_TABLES = [
    "anime_source", "alt_titles", "anime_genres", "anime_themes", "anime_studios",
    "characters", "staff", "episodes", "relationships", "descriptions", "qa_pairs",
    "instructions", "rag_chunks", "franchises",
]

REFERENCE_TABLES = ["genres", "themes", "studios", "license_tiers"]

SYSTEM_TABLES = ["splits", "dedup_log", "provenance", "quality_validation",
                 "checkpoint", "run_log"]


def _jsonl(path: pathlib.Path, records) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def _jsonl_table(conn, path, sql, arrays=(), split=True, tier=True) -> int:
    split_of = dict(conn.execute("select anime_id, split from splits"))
    tier_of = {}
    if tier:
        try:
            tier_of = dict(conn.execute("select anime_id, tier from license_tiers"))
        except Exception:
            tier_of = {}
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in conn.execute(sql):
            d = dict(row)
            for field in arrays:
                try:
                    d[field] = json.loads(d[field] or "[]")
                except (TypeError, json.JSONDecodeError):
                    d[field] = []
            if split and "anime_id" in d:
                d["split"] = split_of.get(d["anime_id"])
            if tier and "anime_id" in d:
                d["license_tier"] = tier_of.get(d["anime_id"])
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
    return n


def _anime_records(conn) -> list[dict]:
    split_of = dict(conn.execute("select anime_id, split from splits"))
    franchise_of = dict(conn.execute("select anime_id, franchise_id from franchises"))
    try:
        tier_of = dict(conn.execute("select anime_id, tier from license_tiers"))
    except Exception:
        tier_of = {}
    alt: dict[int, list[str]] = {}
    genres: dict[int, list[str]] = {}
    themes: dict[int, list[str]] = {}
    studios: dict[int, list[str]] = {}
    sources: dict[int, list[dict]] = {}
    for r in conn.execute("select anime_id, title from alt_titles order by anime_id"):
        alt.setdefault(r[0], []).append(r[1])
    for r in conn.execute("select anime_id, genre from anime_genres order by anime_id"):
        genres.setdefault(r[0], []).append(r[1])
    for r in conn.execute("select anime_id, theme from anime_themes order by anime_id"):
        themes.setdefault(r[0], []).append(r[1])
    for r in conn.execute("select anime_id, studio_name from anime_studios order by anime_id"):
        studios.setdefault(r[0], []).append(r[1])
    for r in conn.execute("select anime_id, source, remote_id, url, link_method, confidence "
                          "from anime_source order by anime_id"):
        sources.setdefault(r[0], []).append(
            {"source": r[1], "remote_id": r[2], "url": r[3],
             "link_method": r[4], "confidence": r[5]})

    records = []
    for row in conn.execute("select * from anime order by anime_id"):
        d = dict(row)
        aid = row["anime_id"]
        # Upstream prose is never exported. The columns remain in the local
        # working database for QA, but every shipped artifact carries only
        # factual fields and project-generated text.
        d.pop("synopsis", None)
        d.pop("synopsis_source", None)
        d["alt_titles"] = alt.get(aid, [])
        d["genres"] = genres.get(aid, [])
        d["themes"] = themes.get(aid, [])
        d["studios"] = studios.get(aid, [])
        d["sources"] = sources.get(aid, [])
        d["franchise_id"] = franchise_of.get(aid)
        d["license_tier"] = tier_of.get(aid)
        d["split"] = split_of.get(aid)
        records.append(d)
    return records


def source_status() -> list[dict]:
    """The per-source registry, in memory.

    Shared with the exporter so the license manifest and `sources.jsonl` cannot
    disagree, and so tier assignment does not depend on the export having run
    yet: `license_tiers` runs *before* `export` precisely so the tier column is
    populated in the files.
    """
    cfg = load()
    return [
        {"source_id": "anilist", "name": "AniList", "url": cfg["anilist"]["url"],
         "source_type": "graphql_api",
         "license": "AniList content is copyright its respective providers and licensed to "
                    "AniList; API use per AniList terms",
         "permission_status": "public_api_no_auth",
         "retrieval_method": "GraphQL light+full batches", "retrieval_date": now(),
         "notes": "primary discovery and enrichment source"},
        {"source_id": "kitsu", "name": "Kitsu", "url": cfg["kitsu"]["url"],
         "source_type": "json_api",
         "license": "Kitsu terms of service; no redistribution grant located",
         "permission_status": "public_api_terms", "retrieval_method": "paginated index + episodes",
         "retrieval_date": now(), "notes": "secondary source and only episode-list provider"},
        {"source_id": "shikimori", "name": "Shikimori", "url": cfg["shikimori"]["url"],
         "source_type": "json_api", "license": "unspecified",
         "permission_status": "public_api_uncertain",
         "retrieval_method": "paginated index + detail + roles + related",
         "retrieval_date": now(),
         "notes": "license_uncertain; recorded as such and never labelled reusable"},
        {"source_id": "wikidata", "name": "Wikidata", "url": "https://wikidata.org/wiki/Q1107",
         "source_type": "sparql", "license": "CC0-1.0", "permission_status": "public_domain_cc0",
         "retrieval_method": "SPARQL query on Q1107 subclasses", "retrieval_date": now(),
         "notes": "supplementary title source"},
        {"source_id": "ann", "name": "Anime News Network Encyclopedia", "url": cfg["ann"]["base"],
         "source_type": "html", "license": "copyrighted",
         "permission_status": "collected_but_not_integrated",
         "retrieval_method": "sample of individual anime.php?id pages", "retrieval_date": now(),
         "notes": "789 sample pages retained in raw storage; zero rows linked into exports"},
        {"source_id": "mal", "name": "MyAnimeList / Jikan", "url": "https://myanimelist.net",
         "source_type": "json_api", "license": "see myanimelist.net",
         "permission_status": "blocked", "retrieval_method": "none", "retrieval_date": now(),
         "notes": "network-blocked from the collection environment; excluded"},
    ]


def sources_registry(path: pathlib.Path) -> int:
    return _jsonl(path, source_status())


def _write_sqlite(conn) -> int:
    db_path = EXPORT_DIR / "anime_dataset.sqlite"
    if db_path.exists():
        db_path.unlink()
    conn.execute("ATTACH DATABASE ? AS exp", (str(db_path),))
    split_join = (" left join main.splits s on s.anime_id = t.anime_id")
    tier_join = (" left join main.license_tiers lt on lt.anime_id = t.anime_id")

    conn.execute("CREATE TABLE exp.anime AS SELECT t.*, s.split AS split, lt.tier AS license_tier "
                 "FROM main.anime t" + split_join + tier_join)
    for table in CHILD_TABLES:
        conn.execute(f"CREATE TABLE exp.{table} AS SELECT t.*, s.split AS split, "
                     f"lt.tier AS license_tier FROM main.{table} t"
                     + split_join + tier_join)
    for table in REFERENCE_TABLES:
        try:
            conn.execute(f"CREATE TABLE exp.{table} AS SELECT * FROM main.{table}")
        except Exception:
            continue
    for table in SYSTEM_TABLES:
        conn.execute(f"CREATE TABLE exp.{table} AS SELECT * FROM main.{table}")

    # The SQLite release copy gets the same content policy as the JSONL files:
    # no upstream synopses, character bios, or episode summaries.
    conn.execute("UPDATE exp.anime SET synopsis=NULL, synopsis_source=NULL")
    conn.execute("UPDATE exp.characters SET description=NULL")
    conn.execute("UPDATE exp.episodes SET synopsis=NULL")
    conn.execute("UPDATE exp.themes SET description=NULL")
    conn.execute("UPDATE exp.genres SET description=NULL")
    conn.execute("DELETE FROM exp.descriptions WHERE kind<>'record_summary'")

    for table in ("anime", "characters", "staff", "episodes", "relationships"):
        conn.execute(f"CREATE INDEX exp.idx_{table}_anime ON {table}(anime_id)")
    conn.execute("CREATE INDEX exp.idx_anime_split ON anime(split)")
    conn.execute("DETACH DATABASE exp")
    conn.commit()
    return 1


def _write_parquet(paths: dict[str, pathlib.Path]) -> int:
    try:
        import pyarrow as pa
        import pyarrow.json as pajson
        import pyarrow.parquet as pq
    except ImportError:
        print("parquet: skipped (pyarrow not installed)")
        return 0

    n = 0
    failed: list[str] = []
    for name, path in paths.items():
        if not path.exists() or path.stat().st_size == 0:
            continue
        # `read_json` is fast and streams, but it cannot infer a schema for the
        # nested objects and arrays our tables contain. Falling back to an
        # explicit Python conversion gives those tables a Parquet form instead
        # of silently dropping them.
        try:
            table = pajson.read_json(path)
        except Exception:
            try:
                rows = []
                with open(path, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            rows.append(json.loads(line))
                table = pa.Table.from_pylist(rows)
                del rows
            except Exception as exc:  # pragma: no cover - environment dependent
                failed.append(f"{name} ({type(exc).__name__}: {exc})")
                continue
        pq.write_table(table, EXPORT_DIR / f"{name}.parquet")
        n += 1
    if failed:
        print("parquet: could not convert " + "; ".join(failed))
    return n


def main(argv=None) -> int:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    counts = {}

    anime = _anime_records(conn)
    counts["anime"] = _jsonl(EXPORT_DIR / "anime.jsonl", anime)

    counts["characters"] = _jsonl_table(
        conn, EXPORT_DIR / "characters.jsonl",
        "select id, anime_id, source, remote_id, name, name_native, name_ru, role, "
        "voice_actors, source_refs from characters order by id",
        arrays=("voice_actors", "source_refs"))
    counts["staff"] = _jsonl_table(
        conn, EXPORT_DIR / "staff.jsonl",
        "select id, anime_id, source, remote_id, name, name_native, name_ru, roles, source_refs "
        "from staff order by id", arrays=("roles", "source_refs"))
    counts["studios"] = _jsonl(EXPORT_DIR / "studios.jsonl",
        [dict(zip(("studio_name", "source_studio_id", "url"), r)) for r in conn.execute(
            "select studio_name, source_studio_id, url from studios order by studio_name")])
    counts["genres"] = _jsonl(EXPORT_DIR / "genres.jsonl",
        [{"genre": r[0]} for r in conn.execute(
            "select genre from genres order by genre")])
    # Theme definitions are AniList tag prose, so only the label ships.
    counts["themes"] = _jsonl(EXPORT_DIR / "themes.jsonl",
        [{"theme": r[0]} for r in conn.execute(
            "select theme from themes order by theme")])
    counts["episodes"] = _jsonl_table(
        conn, EXPORT_DIR / "episodes.jsonl",
        "select id, anime_id, source, remote_id, number, title, aired, length_min "
        "from episodes order by id")
    counts["relationships"] = _jsonl_table(
        conn, EXPORT_DIR / "relationships.jsonl",
        "select anime_id, other_anime_id, other_source, other_remote_id, relation, source "
        "from relationships order by anime_id")
    counts["qa"] = _jsonl_table(
        conn, EXPORT_DIR / "qa.jsonl",
        "select id, anime_id, qtype, question, answer, template, grounded_fields "
        "from qa_pairs order by id", arrays=("grounded_fields",))
    counts["instructions"] = _jsonl_table(
        conn, EXPORT_DIR / "instructions.jsonl",
        "select id, anime_id, itype, instruction, input, output, synthetic, source_record_ids, "
        "purpose, validation from instructions order by id", arrays=("source_record_ids",))
    counts["rag_chunks"] = _jsonl_table(
        conn, EXPORT_DIR / "rag_chunks.jsonl",
        "select id, anime_id, chunk_index, kind, text, source_refs from rag_chunks order by id",
        arrays=("source_refs",))
    counts["alt_titles"] = _jsonl_table(
        conn, EXPORT_DIR / "alt_titles.jsonl",
        "select anime_id, source, lang, kind, title, sources from alt_titles order by anime_id",
        arrays=("sources",))
    counts["descriptions"] = _jsonl_table(
        conn, EXPORT_DIR / "descriptions.jsonl",
        "select anime_id, kind, text, synthetic, provenance from descriptions order by anime_id")
    counts["entity_links"] = _jsonl_table(
        conn, EXPORT_DIR / "entity_links.jsonl",
        "select anime_id, source, remote_id, url, link_method, confidence "
        "from anime_source order by anime_id")
    counts["franchises"] = _jsonl_table(
        conn, EXPORT_DIR / "franchises.jsonl",
        "select franchise_id, anime_id from franchises order by franchise_id")
    counts["dedup_merge_log"] = _jsonl(EXPORT_DIR / "dedup_merge_log.jsonl",
        [dict(zip(("cluster_id", "canonical_anime_id", "method", "members", "created_at"), r))
         for r in conn.execute("select cluster_id, canonical_anime_id, method, members, "
                               "created_at from dedup_log order by cluster_id")])
    counts["provenance"] = _jsonl(EXPORT_DIR / "provenance.jsonl",
        [dict(zip(("entity", "entity_id", "source", "url", "retrieved_at", "license_note",
                   "confidence"), r)) for r in conn.execute(
            "select entity, entity_id, source, url, retrieved_at, license_note, confidence "
            "from provenance order by id")])
    counts["sources"] = sources_registry(EXPORT_DIR / "sources.jsonl")
    try:
        counts["license_tiers"] = _jsonl(EXPORT_DIR / "license_tiers.jsonl",
            [dict(zip(("anime_id", "tier", "sources", "reason"), r)) for r in conn.execute(
                "select anime_id, tier, sources, reason from license_tiers order by anime_id")])
    except Exception:
        counts["license_tiers"] = 0

    with open(EXPORT_DIR / "anime.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["anime_id", "title_canonical", "title_english", "title_japanese", "type",
                    "status", "episodes", "duration_min", "aired_from", "aired_to", "year",
                    "season", "source_material", "mean_score", "favourites", "genres", "themes",
                    "studios", "franchise_id", "license_tier", "split"])
        for d in anime:
            w.writerow([d["anime_id"], d["title_canonical"], d["title_english"],
                        d["title_japanese"], d["type"], d["status"], d["episodes"],
                        d["duration_min"], d["aired_from"], d["aired_to"], d["year"],
                        d["season"], d["source_material"], d["mean_score"], d["favourites"],
                        "|".join(d["genres"]), "|".join(d["themes"]),
                        "|".join(d["studios"]), d["franchise_id"], d["license_tier"],
                        d["split"]])
    counts["anime_csv"] = len(anime)

    counts["parquet"] = _write_parquet({
        name: EXPORT_DIR / f"{name}.jsonl" for name in (
            "anime", "qa", "rag_chunks", "instructions", "characters", "staff",
            "episodes", "relationships", "descriptions", "alt_titles")
    })

    counts["sqlite_export"] = _write_sqlite(conn)

    cp_set(conn, "export_done", True)
    log(conn, "export", json.dumps(counts))
    print(json.dumps(counts, indent=2))
    conn.close()
    return 0
