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
from .attribution import PROSE_FIELDS, normalize_source

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


def _jsonl_table(conn, path, sql, arrays=(), split=True, tier=True, table=None) -> int:
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
            if table:
                field, source_field = PROSE_FIELDS.get(table, (None, None))
                if field:
                    is_prose = bool(d.get(field))
                    if table == "descriptions":
                        is_prose = d.get("kind") == "source_synopsis"
                    elif table == "qa_pairs":
                        is_prose = d.get("qtype") == "synopsis"
                    elif table == "rag_chunks":
                        is_prose = d.get("kind") == "source_synopsis"
                    if is_prose:
                        source = normalize_source(d.get(source_field))
                        d["prose_source"] = source
                        d["prose_license"] = _prose_license(source)
                    else:
                        d["prose_source"] = None
                        d["prose_license"] = None
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
    return n


_PROSE_LICENSE: dict[str, str] | None = None


def _prose_license(source: str) -> str:
    """Redistribution status for one prose source, from the shared registry."""
    global _PROSE_LICENSE
    if _PROSE_LICENSE is None:
        _PROSE_LICENSE = {s["source_id"]: s["redistribution"] for s in source_status()}
        _PROSE_LICENSE["unknown"] = "unresolved"
    return _PROSE_LICENSE.get(source, "unresolved")


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
        # Upstream prose ships only with its source attached. Attribution does
        # not make the text CC-BY: `prose_license` carries the source's actual
        # redistribution status so a consumer can filter it out.
        if d.get("synopsis"):
            source = normalize_source(d.get("synopsis_source"))
            d["prose_source"] = source
            d["prose_license"] = _prose_license(source)
        else:
            d["prose_source"] = None
            d["prose_license"] = None
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
        {"source_id": "anilist", "name": "AniList", "owner": "AniList",
         "url": cfg["anilist"]["url"], "terms_url": "https://anilist.co/terms",
         "source_type": "graphql_api",
         "data_license": "AniList Terms of Service; content remains copyright its providers",
         "license": "AniList terms of service; no redistribution grant",
         "redistribution": "permission_required",
         "attribution_text": "AniList (anilist.co)",
         "prose_fields": ["anime.synopsis", "characters.description", "themes.description"],
         "permission_status": "public_api_no_auth",
         "retrieval_method": "GraphQL light+full batches", "retrieval_date": now(),
         "notes": "primary discovery and enrichment source"},
        {"source_id": "kitsu", "name": "Kitsu", "owner": "Kitsu",
         "url": cfg["kitsu"]["url"], "terms_url": "https://kitsu.io/terms",
         "source_type": "json_api",
         "data_license": "Kitsu Terms of Service; no data redistribution grant located",
         "license": "Kitsu terms of service; no redistribution grant located",
         "redistribution": "permission_required",
         "attribution_text": "Kitsu (kitsu.io)",
         "prose_fields": ["anime.synopsis", "episodes.synopsis"],
         "permission_status": "public_api_terms", "retrieval_method": "paginated index + episodes",
         "retrieval_date": now(), "notes": "secondary source and only episode-list provider"},
        {"source_id": "shikimori", "name": "Shikimori", "owner": "Shikimori",
         "url": cfg["shikimori"]["url"], "terms_url": "https://shikimori.io/terms",
         "source_type": "json_api",
         "data_license": "Shikimori user agreement (2012); no data-reuse or redistribution "
                         "grant located",
         "license": "user agreement found; no data-reuse grant",
         "redistribution": "unresolved",
         "attribution_text": "Shikimori (shikimori.io)",
         "prose_fields": ["anime.synopsis", "characters.description"],
         "permission_status": "public_api_uncertain",
         "retrieval_method": "paginated index + detail + roles + related",
         "retrieval_date": now(),
         "notes": "terms page located at shikimori.io/terms; it is a general user agreement, "
                  "not a data licence, so redistribution is unresolved"},
        {"source_id": "wikidata", "name": "Wikidata",
         "owner": "Wikimedia Foundation / Wikidata contributors",
         "url": "https://wikidata.org/wiki/Q1107",
         "terms_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
         "source_type": "sparql", "data_license": "CC0-1.0",
         "license": "CC0-1.0", "redistribution": "allowed",
         "attribution_text": "Wikidata contributors (CC0-1.0)",
         "prose_fields": [],
         "permission_status": "public_domain_cc0",
         "retrieval_method": "SPARQL query on Q1107 subclasses", "retrieval_date": now(),
         "notes": "supplementary title source"},
        {"source_id": "ann", "name": "Anime News Network Encyclopedia",
         "owner": "Anime News Network", "url": cfg["ann"]["base"], "terms_url": None,
         "source_type": "html", "data_license": "copyrighted; no terms page located",
         "license": "copyrighted", "redistribution": "unresolved",
         "attribution_text": "Anime News Network (animenewsnetwork.com)",
         "prose_fields": [],
         "permission_status": "collected_but_not_integrated",
         "retrieval_method": "sample of individual anime.php?id pages", "retrieval_date": now(),
         "notes": "789 sample pages retained in raw storage; zero rows linked into exports"},
        {"source_id": "mal", "name": "MyAnimeList / Jikan", "owner": "MyAnimeList",
         "url": "https://myanimelist.net",
         "terms_url": "https://myanimelist.net/about/terms_of_use",
         "source_type": "json_api", "data_license": "not collected",
         "license": "see myanimelist.net", "redistribution": "blocked",
         "attribution_text": "MyAnimeList (myanimelist.net)",
         "prose_fields": [],
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

    # Prose is retained in the SQLite copy. Its native source columns travel
    # with it, and normalised `prose_source` / `prose_license` columns are added
    # so the SQLite contract matches the JSONL files.
    for table in ("anime", "characters", "episodes", "themes", "descriptions"):
        conn.execute(f"ALTER TABLE exp.{table} ADD COLUMN prose_source TEXT")
        conn.execute(f"ALTER TABLE exp.{table} ADD COLUMN prose_license TEXT")
    # qa_pairs and rag_chunks already carry `prose_source` from the pipeline;
    # only the licence status needs adding.
    for table in ("qa_pairs", "rag_chunks"):
        conn.execute(f"ALTER TABLE exp.{table} ADD COLUMN prose_license TEXT")

    def source_expr(column: str) -> str:
        return (
            f"CASE WHEN {column} IS NULL OR trim({column})='' THEN 'unknown' "
            f"WHEN {column} LIKE 'kitsu%' THEN 'kitsu' "
            f"WHEN {column} LIKE 'anilist%' THEN 'anilist' "
            f"WHEN {column} LIKE 'shikimori%' THEN 'shikimori' "
            f"WHEN {column} LIKE 'wikidata%' THEN 'wikidata' "
            f"ELSE 'unknown' END")

    def license_expr(expr: str) -> str:
        return (
            f"CASE WHEN {expr} IN ('anilist','kitsu') THEN 'permission_required' "
            f"WHEN {expr} = 'wikidata' THEN 'allowed' "
            f"ELSE 'unresolved' END")

    prose_updates = (
        ("anime", "synopsis", "synopsis_source"),
        ("characters", "description", "source"),
        ("episodes", "synopsis", "source"),
        ("themes", "description", "description_source"),
    )
    for table, prose_col, source_col in prose_updates:
        src = source_expr(source_col)
        conn.execute(
            f"UPDATE exp.{table} SET prose_source={src}, prose_license={license_expr(src)} "
            f"WHERE {prose_col} IS NOT NULL AND trim({prose_col})<>''")
    conn.execute(
        "UPDATE exp.descriptions SET prose_source=" + source_expr("source") +
        ", prose_license=" + license_expr(source_expr("source")) +
        " WHERE kind='source_synopsis'")
    for table, prose_kind in (("qa_pairs", "qtype='synopsis'"),
                              ("rag_chunks", "kind='source_synopsis'")):
        conn.execute(
            f"UPDATE exp.{table} SET prose_source=coalesce(nullif(prose_source,''),'unknown'), "
            f"prose_license={license_expr('prose_source')} WHERE {prose_kind}")

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


def write_attribution() -> int:
    """Write the field-level attribution registry.

    `unknown` is a first-class entry, not an omission: if a prose row ever ships
    without a source label it is exported as `unknown` and tiered `unresolved`,
    and consumers need a record to point at.
    """
    sources = [
        {k: s[k] for k in ("source_id", "name", "owner", "url", "terms_url",
                           "data_license", "redistribution", "attribution_text",
                           "prose_fields", "notes")}
        for s in source_status()
    ]
    sources.append({
        "source_id": "unknown",
        "name": "Unrecorded upstream source",
        "owner": "unknown",
        "url": None,
        "terms_url": None,
        "data_license": "no source label recorded",
        "redistribution": "unresolved",
        "attribution_text": "source unknown",
        "prose_fields": ["anime.synopsis", "characters.description",
                         "episodes.synopsis", "themes.description"],
        "notes": "Rows in this bucket have upstream prose but no verified source label. "
                 "They are exported as `unknown` and must not be treated as reusable.",
    })
    attribution = {
        "generated_at": now(),
        "notice": (
            "Upstream prose is excluded from the project's CC-BY-4.0 grant. Each field "
            "remains subject to the named source's terms; attribution is not permission."
        ),
        "sources": sources,
    }
    (EXPORT_DIR / "attribution.json").write_text(
        json.dumps(attribution, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(sources)


def main(argv=None) -> int:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    counts = {}

    anime = _anime_records(conn)
    counts["anime"] = _jsonl(EXPORT_DIR / "anime.jsonl", anime)

    counts["characters"] = _jsonl_table(
        conn, EXPORT_DIR / "characters.jsonl",
        "select id, anime_id, source, remote_id, name, name_native, name_ru, role, "
        "description, voice_actors, source_refs from characters order by id",
        arrays=("voice_actors", "source_refs"), table="characters")
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
    counts["themes"] = _jsonl_table(
        conn, EXPORT_DIR / "themes.jsonl",
        "select theme, description, description_source from themes order by theme",
        split=False, tier=False, table="themes")
    counts["episodes"] = _jsonl_table(
        conn, EXPORT_DIR / "episodes.jsonl",
        "select id, anime_id, source, remote_id, number, title, synopsis, aired, length_min "
        "from episodes order by id", table="episodes")
    counts["relationships"] = _jsonl_table(
        conn, EXPORT_DIR / "relationships.jsonl",
        "select anime_id, other_anime_id, other_source, other_remote_id, relation, source "
        "from relationships order by anime_id")
    counts["qa"] = _jsonl_table(
        conn, EXPORT_DIR / "qa.jsonl",
        "select id, anime_id, qtype, question, answer, template, grounded_fields, prose_source "
        "from qa_pairs order by id", arrays=("grounded_fields",), table="qa_pairs")
    counts["instructions"] = _jsonl_table(
        conn, EXPORT_DIR / "instructions.jsonl",
        "select id, anime_id, itype, instruction, input, output, synthetic, source_record_ids, "
        "purpose, validation from instructions order by id", arrays=("source_record_ids",))
    counts["rag_chunks"] = _jsonl_table(
        conn, EXPORT_DIR / "rag_chunks.jsonl",
        "select id, anime_id, chunk_index, kind, text, source_refs, prose_source "
        "from rag_chunks order by id",
        arrays=("source_refs",), table="rag_chunks")
    counts["alt_titles"] = _jsonl_table(
        conn, EXPORT_DIR / "alt_titles.jsonl",
        "select anime_id, source, lang, kind, title, sources from alt_titles order by anime_id",
        arrays=("sources",))
    counts["descriptions"] = _jsonl_table(
        conn, EXPORT_DIR / "descriptions.jsonl",
        "select anime_id, kind, text, synthetic, provenance, source from descriptions "
        "order by anime_id", table="descriptions")
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
    counts["attribution"] = write_attribution()
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
