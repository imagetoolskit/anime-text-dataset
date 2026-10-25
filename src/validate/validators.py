"""Dataset validation.

Checks fall into four groups: coverage gates, structural integrity, value
domains, and grounding of the generated text. Every check writes a row to
`quality_validation` so the report can show what passed without rerunning.
"""

import json
import random
import re
import unicodedata

from ..config import load
from ..db import ROOT, connect, log

ALLOWED_TYPE = {"TV", "MOVIE", "OVA", "ONA", "SPECIAL", "TV_SPECIAL", "SHORT", "TV_SHORT",
                "ONA_SHORT", "MUSIC", "PV", "CM"}
ALLOWED_STATUS = {"FINISHED", "RELEASING", "NOT_YET_RELEASED", "CANCELLED", "HIATUS"}
ALLOWED_SEASON = {"WINTER", "SPRING", "SUMMER", "FALL"}
ALLOWED_SOURCE = {"ORIGINAL", "MANGA", "LIGHT_NOVEL", "NOVEL", "WEB_NOVEL", "WEB_MANGA",
                  "VISUAL_NOVEL", "VIDEO_GAME", "CARD_GAME", "GAME", "ANIME", "MUSIC",
                  "BOOK", "PICTURE_BOOK", "RADIO", "LIVE_ACTION", "MIXED_MEDIA",
                  "DOUJINSHI", "OTHER"}
ALLOWED_AGE = {"G", "PG", "PG-13", "R", "R+", "RX"}
ALLOWED_ROLE = {"Main", "Supporting", "Background"}
ALLOWED_RELATION = {"SEQUEL", "PREQUEL", "PARENT_STORY", "FULL_STORY", "SIDE_STORY",
                    "SPIN_OFF", "ALTERNATIVE", "ALTERNATIVE_SETTING", "ALTERNATIVE_VERSION",
                    "SUMMARY", "ADAPTATION", "CHARACTER", "SAME_SERIES", "SOURCE",
                    "COMPILATION", "CONTAINS", "OTHER"}
ALLOWED_TIER = {"cc0_only", "permission_required", "unresolved"}
MAX_YEAR = 2031

FIELD_SQL = {
    "type": "a.type is not null",
    "status": "a.status is not null",
    "year": "a.year is not null",
    "aired_from": "a.aired_from is not null",
    "episodes": "a.episodes is not null",
    "duration_min": "a.duration_min is not null",
    "mean_score": "a.mean_score is not null",
    "favourites": "a.favourites is not null",
    "popularity": "a.popularity is not null",
    "source_material": "a.source_material is not null",
    "title_english": "a.title_english is not null",
    "title_japanese": "a.title_japanese is not null",
    "studios": "exists (select 1 from anime_studios x where x.anime_id=a.anime_id)",
    "genres": "exists (select 1 from anime_genres x where x.anime_id=a.anime_id)",
    "themes": "exists (select 1 from anime_themes x where x.anime_id=a.anime_id)",
    "alt_titles": "exists (select 1 from alt_titles x where x.anime_id=a.anime_id)",
    "characters": "exists (select 1 from characters x where x.anime_id=a.anime_id)",
    "characters.role": "exists (select 1 from characters x where x.anime_id=a.anime_id and x.role is not null)",
    "characters.voice_actors": "exists (select 1 from characters x where x.anime_id=a.anime_id and x.voice_actors is not null)",
    "staff.roles": "exists (select 1 from staff x where x.anime_id=a.anime_id and x.roles is not null)",
    "episodes.title": "exists (select 1 from episodes x where x.anime_id=a.anime_id and x.title is not null)",
    "relationships": "exists (select 1 from relationships x where x.anime_id=a.anime_id)",
    "franchises": "exists (select 1 from franchises x where x.anime_id=a.anime_id)",
}


def _norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKC", (t or "")).casefold()
    for ch in "·・:：!！?？,，.。\"'“”‘’()[]{}<>-–—_ ":
        t = t.replace(ch, "")
    return t.strip()


def record(conn, name, status, detail=None, target=None):
    conn.execute("INSERT INTO quality_validation(check_name,target,status,detail) VALUES(?,?,?,?)",
                 (name, target, status, detail))


def check_min_titles(conn, cfg) -> bool:
    n = conn.execute("select count(*) from anime where title_canonical is not null "
                     "or title_english is not null").fetchone()[0]
    ok = n >= cfg["min_anime_titles"]
    record(conn, "min_anime_titles", "pass" if ok else "fail",
           f"{n} unique anime with titles (required {cfg['min_anime_titles']}, "
           f"target {cfg['target_anime_titles']})")
    return ok


def check_unique_source_ids(conn) -> bool:
    n = conn.execute("select count(*) from (select source, remote_id, count(*) c "
                     "from anime_source group by 1,2 having c>1)").fetchone()[0]
    ok = n == 0
    record(conn, "unique_source_remote_ids", "pass" if ok else "fail",
           f"{n} duplicated (source, remote_id) pairs")
    return ok


def check_no_orphans(conn) -> bool:
    checks = [
        ("anime_source", "select count(*) from anime_source where anime_id not in (select anime_id from anime)"),
        ("alt_titles", "select count(*) from alt_titles where anime_id not in (select anime_id from anime)"),
        ("anime_genres", "select count(*) from anime_genres where anime_id not in (select anime_id from anime)"),
        ("anime_themes", "select count(*) from anime_themes where anime_id not in (select anime_id from anime)"),
        ("anime_studios", "select count(*) from anime_studios where anime_id not in (select anime_id from anime)"),
        ("characters", "select count(*) from characters where anime_id not in (select anime_id from anime)"),
        ("staff", "select count(*) from staff where anime_id not in (select anime_id from anime)"),
        ("episodes", "select count(*) from episodes where anime_id not in (select anime_id from anime)"),
        ("relationships", "select count(*) from relationships where anime_id not in (select anime_id from anime)"),
        ("qa_pairs", "select count(*) from qa_pairs where anime_id not in (select anime_id from anime)"),
        ("instructions", "select count(*) from instructions where anime_id not in (select anime_id from anime)"),
        ("rag_chunks", "select count(*) from rag_chunks where anime_id not in (select anime_id from anime)"),
        ("descriptions", "select count(*) from descriptions where anime_id not in (select anime_id from anime)"),
        ("splits", "select count(*) from splits where anime_id not in (select anime_id from anime)"),
    ]
    bad = []
    for name, sql in checks:
        n = conn.execute(sql).fetchone()[0]
        if n:
            bad.append(f"{name}: {n}")
    ok = not bad
    record(conn, "referential_integrity", "pass" if ok else "fail",
           "; ".join(bad) or "no orphans")
    return ok


def check_no_duplicate_titles(conn) -> bool:
    """Two rows with the same normalized title *and* the same known year are a
    duplicate. Rows with an unknown year are not compared: the same title in an
    unknown year is not evidence that two works are the same one."""
    seen: dict[tuple[str, int], int] = {}
    dup = []
    skipped_unknown_year = 0
    for aid, t, y in conn.execute(
            "select anime_id, coalesce(title_canonical, title_english), year from anime "
            "where title_canonical is not null or title_english is not null"):
        if y is None:
            skipped_unknown_year += 1
            continue
        nt = _norm_title(t)
        if not nt or not any(ch.isalnum() for ch in nt):
            continue
        key = (nt, y)
        if key in seen:
            dup.append((aid, seen[key], t, y))
        else:
            seen[key] = aid
    ok = not dup
    record(conn, "no_duplicate_title_year", "pass" if ok else "fail",
           f"{len(dup)} same-title+year collisions"
           + (f": {dup[:5]}" if dup else "")
           + f"; {skipped_unknown_year} rows with no year not compared")
    return ok


def check_enum_domains(conn) -> bool:
    def offending(sql: str, allowed: set[str]) -> list[str]:
        return [r[0] for r in conn.execute(sql) if r[0] not in allowed]

    bad_type = offending("select distinct type from anime where type is not null", ALLOWED_TYPE)
    bad_status = offending("select distinct status from anime where status is not null", ALLOWED_STATUS)
    bad_season = offending("select distinct season from anime where season is not null", ALLOWED_SEASON)
    bad_source = offending("select distinct source_material from anime "
                           "where source_material is not null", ALLOWED_SOURCE)
    bad_age = offending("select distinct age_rating from anime where age_rating is not null",
                        ALLOWED_AGE)
    bad_role = offending("select distinct role from characters where role is not null",
                         ALLOWED_ROLE)
    bad_rel = offending("select distinct relation from relationships where relation is not null",
                        ALLOWED_RELATION)
    ok = not (bad_type or bad_status or bad_season or bad_source or bad_age or bad_role or bad_rel)
    record(conn, "enum_conformance", "pass" if ok else "fail",
           f"type={bad_type[:5]} status={bad_status[:5]} season={bad_season[:5]} "
           f"source_material={bad_source[:5]} age_rating={bad_age[:5]} "
           f"role={bad_role[:5]} relation={bad_rel[:5]}")
    return ok


def check_value_ranges(conn) -> bool:
    zero_scores = conn.execute("select count(*) from anime where mean_score=0").fetchone()[0]
    bad_scores = conn.execute("select count(*) from anime where mean_score<0 "
                              "or mean_score>100").fetchone()[0]
    bad_years = conn.execute(
        "select count(*) from anime where year is not null and (year<1900 or year>?)",
        (MAX_YEAR,)).fetchone()[0]
    bad_eps = conn.execute("select count(*) from anime where episodes is not null "
                           "and (episodes<=0 or episodes>20000)").fetchone()[0]
    ok = zero_scores == 0 and bad_scores == 0 and bad_years == 0 and bad_eps == 0
    record(conn, "value_ranges", "pass" if ok else "fail",
           f"zero_scores={zero_scores} out_of_range_scores={bad_scores} "
           f"bad_years={bad_years} bad_episode_counts={bad_eps}")
    return ok


def check_entity_duplicates(conn) -> bool:
    char_dup = conn.execute(
        "select count(*) from (select anime_id, lower(name) n, count(*) c from characters "
        "group by 1,2 having c>1)").fetchone()[0]
    staff_dup = conn.execute(
        "select count(*) from (select anime_id, lower(name) n, count(*) c from staff "
        "group by 1,2 having c>1)").fetchone()[0]
    rel_dup = conn.execute(
        "select count(*) from (select anime_id, other_anime_id, relation, count(*) c "
        "from relationships group by 1,2,3 having c>1)").fetchone()[0]
    alt_dup = conn.execute(
        "select count(*) from (select anime_id, lower(title) t, count(*) c from alt_titles "
        "group by 1,2 having c>1)").fetchone()[0]
    ep_dup = conn.execute(
        "select count(*) from (select anime_id, number, count(*) c from episodes "
        "group by 1,2 having c>1)").fetchone()[0]
    ok = not (char_dup or staff_dup or rel_dup or alt_dup or ep_dup)
    record(conn, "entity_duplicates", "pass" if ok else "fail",
           f"characters={char_dup} staff={staff_dup} relationships={rel_dup} "
           f"alt_titles={alt_dup} episodes={ep_dup}")
    return ok


def check_name_semantics(conn) -> bool:
    cyr = conn.execute(
        "select count(*) from characters where name_native glob '*[А-Яа-я]*'").fetchone()[0]
    cyr += conn.execute(
        "select count(*) from staff where name_native glob '*[А-Яа-я]*'").fetchone()[0]
    empty_ru = conn.execute(
        "select count(*) from characters where name_ru is null and name_native is null").fetchone()[0]
    ok = cyr == 0
    record(conn, "name_field_semantics", "pass" if ok else "fail",
           f"{cyr} Cyrillic values still in name_native; {empty_ru} characters with neither "
           f"native nor localized name")
    return ok


def check_relationship_integrity(conn) -> bool:
    self_loops = conn.execute("select count(*) from relationships where anime_id=other_anime_id").fetchone()[0]
    dangling = conn.execute(
        "select count(*) from relationships where other_anime_id is not null "
        "and other_anime_id not in (select anime_id from anime)").fetchone()[0]
    ok = self_loops == 0 and dangling == 0
    record(conn, "relationship_integrity", "pass" if ok else "fail",
           f"self_loops={self_loops} dangling_targets={dangling}")
    return ok


def check_split_leakage(conn) -> bool:
    dup = conn.execute("select count(*) from (select anime_id from splits group by 1 "
                       "having count(*)>1)").fetchone()[0]
    total = conn.execute("select count(*) from splits").fetchone()[0]
    anime = conn.execute("select count(*) from anime").fetchone()[0]
    ok = dup == 0 and total == anime
    record(conn, "split_coverage", "pass" if ok else "fail",
           f"{total} split rows for {anime} anime, {dup} duplicates")
    return ok


def check_split_proportions(conn) -> bool:
    total = conn.execute("select count(*) from splits").fetchone()[0]
    if not total:
        record(conn, "split_proportions", "fail", "no splits assigned")
        return False
    counts = dict(conn.execute("select split, count(*) from splits group by split"))
    p = {k: v / total for k, v in counts.items()}
    ok = (abs(p.get("train", 0) - 0.90) <= 0.02 and abs(p.get("val", 0) - 0.05) <= 0.02
          and abs(p.get("test", 0) - 0.05) <= 0.02)
    record(conn, "split_proportions", "pass" if ok else "fail", f"{counts} of {total}")
    return ok


def check_qa_grounding(conn) -> bool:
    n = conn.execute("select count(*) from qa_pairs").fetchone()[0]
    empty = conn.execute("select count(*) from qa_pairs where grounded_fields is null "
                         "or grounded_fields='[]'").fetchone()[0]
    badtpl = conn.execute("select count(*) from qa_pairs where question like '%{%' "
                          "or answer like '%{%'").fetchone()[0]
    # Python/JSON sentinels leak as a value in a sentence: "... is None." A naive
    # word match also hits legitimate names and titles ("Nan to Jo-sensei",
    # "Koi nan desu") and quoted episode titles ("Box 3 None of your business!!"),
    # so match a sentinel where a value would end and ignore quoted spans.
    quoted = re.compile(r'"[^"]*"')
    sentinel = re.compile(
        r"(?:^|[\s(])(None|NaN|nan|null|NULL|undefined|inf|-inf)(?=[.,;:)\]]|$)")
    # Titles legitimately contain sentinel-looking words ("Party of None",
    # "Koi nan desu"). Collect only those, strip them from a candidate answer,
    # then test what is left.
    title_rows = conn.execute(
        "select title_canonical a, title_english b, title_japanese c from anime").fetchall()
    titles = set()
    for row in title_rows:
        titles.update(t for t in row if t)
    titles.update(r[0] for r in conn.execute("select title from alt_titles") if r[0])
    sentinel_titles = sorted((t for t in titles if sentinel.search(t)),
                             key=len, reverse=True)

    placeholder = 0
    leaks = []
    for row in conn.execute("select id, answer from qa_pairs"):
        text = quoted.sub('""', row["answer"] or "")
        if not sentinel.search(text):
            continue
        for title in sentinel_titles:
            if title in text:
                text = text.replace(title, " ")
        if sentinel.search(text):
            placeholder += 1
            if len(leaks) < 3:
                leaks.append(row["id"])
    ok = n > 0 and empty == 0 and badtpl == 0 and placeholder == 0
    record(conn, "qa_grounding", "pass" if ok else "fail",
           f"{n} pairs, {empty} ungrounded, {badtpl} unresolved placeholders, "
           f"{placeholder} leaked sentinels{(' e.g. ' + str(leaks)) if leaks else ''}")
    return ok


def check_qa_field_resolution(conn, sample: int = 5000) -> bool:
    rows = conn.execute(
        "select qtype, anime_id, grounded_fields from qa_pairs order by random() limit ?",
        (sample,)).fetchall()
    bad = []
    for r in rows:
        try:
            fields = json.loads(r["grounded_fields"] or "[]")
        except json.JSONDecodeError:
            bad.append((r["anime_id"], "bad json"))
            continue
        # Abstention rows ground on the *absence* of a field: `unknown_episodes`
        # is only valid when `episodes` is null. Every other row must resolve.
        abstention = (r["qtype"] or "").startswith("unknown_")
        multi_hop = (r["qtype"] or "").startswith("multi_hop_")
        for f in fields:
            sql = FIELD_SQL.get(f)
            if sql is None:
                continue
            if multi_hop and f != "relationships":
                # A multi-hop row asks about the *related* work, so resolve the
                # hop target through any linked anime rather than the subject.
                # `relationships` is the navigation field and belongs to the
                # subject, so it is checked against the subject below.
                present = conn.execute(
                    "select exists (select 1 from relationships rl "
                    "join anime a on a.anime_id = rl.other_anime_id "
                    f"where rl.anime_id=? and {sql})",
                    (r["anime_id"],)).fetchone()[0]
            else:
                present = conn.execute(
                    f"select exists (select 1 from anime a where a.anime_id=? and {sql})",
                    (r["anime_id"],)).fetchone()[0]
            if abstention and present:
                bad.append((r["anime_id"], f"abstained on populated {f}"))
                break
            if not abstention and not present:
                bad.append((r["anime_id"], f))
                break
    ok = len(bad) <= max(2, len(rows) // 200)
    record(conn, "qa_fields_resolve", "pass" if ok else "fail",
           f"{len(bad)} unresolved of {len(rows)} sampled pairs; examples {bad[:5]}")
    return ok


def check_qa_diversity(conn) -> bool:
    types = conn.execute("select count(distinct qtype) from qa_pairs").fetchone()[0]
    templates = conn.execute("select count(distinct template) from qa_pairs").fetchone()[0]
    top = conn.execute("select count(*) from (select template, count(*) c from qa_pairs "
                       "group by 1 order by c desc limit 1)").fetchone()[0]
    total = conn.execute("select count(*) from qa_pairs").fetchone()[0] or 1
    share = top / total
    ok = types >= 10 and templates >= 20 and share < 0.15
    record(conn, "qa_diversity", "pass" if ok else "fail",
           f"{types} question types, {templates} templates, largest template share {share:.1%}")
    return ok


def check_instruction_grounding(conn, sample: int = 3000) -> bool:
    n = conn.execute("select count(*) from instructions").fetchone()[0]
    empty_input = conn.execute("select count(*) from instructions where input is null "
                               "or trim(input)=''").fetchone()[0]
    rows = conn.execute(
        "select itype, input, output from instructions "
        "where itype in ('metadata_extraction','json_repair') order by random() limit ?",
        (sample,)).fetchall()
    bad = []
    for r in rows:
        try:
            out = json.loads(r["output"])
        except json.JSONDecodeError:
            bad.append("unparseable output")
            continue
        values = out.values() if isinstance(out, dict) else [out]
        for v in values:
            items = v if isinstance(v, list) else [v]
            for item in items:
                if item is None or isinstance(item, bool):
                    continue
                if str(item) not in r["input"]:
                    bad.append(f"{r['itype']}: {item!r} missing from input")
                    break
    ok = empty_input == 0 and len(bad) == 0
    record(conn, "instruction_input_grounding", "pass" if ok else "fail",
           f"{n} rows, {empty_input} empty inputs, {len(bad)} sampled output values absent "
           f"from input; examples {bad[:3]}")
    return ok


def check_instruction_diversity(conn) -> bool:
    types = conn.execute("select count(distinct itype) from instructions").fetchone()[0]
    total = conn.execute("select count(*) from instructions").fetchone()[0] or 1
    top = conn.execute("select count(*) from (select itype, count(*) c from instructions "
                       "group by 1 order by c desc limit 1)").fetchone()[0]
    ok = types >= 8 and top / total < 0.5
    record(conn, "instruction_diversity", "pass" if ok else "fail",
           f"{types} instruction types, largest share {top / total:.1%}")
    return ok


def check_rag_quality(conn) -> bool:
    n = conn.execute("select count(*) from rag_chunks").fetchone()[0]
    tiny = conn.execute("select count(*) from rag_chunks where length(text)<30").fetchone()[0]
    not_sentence = conn.execute(
        "select count(*) from rag_chunks where trim(text) not like '%.'").fetchone()[0]
    no_refs = conn.execute("select count(*) from rag_chunks where source_refs is null "
                           "or source_refs='[]'").fetchone()[0]
    raw_json = conn.execute(
        "select count(*) from rag_chunks where text glob '{\"*' "
        "or text glob '[{\"*' or text like '%{\"anime_id\":%'").fetchone()[0]
    try:
        no_kind = conn.execute(
            "select count(*) from rag_chunks where kind is null or kind=''").fetchone()[0]
    except Exception:
        no_kind = n
    # Length alone is a poor quality signal: "X is a TV series from 2019." is a
    # legitimate retrieval unit. What matters is that a chunk is a complete
    # sentence rather than a fragment or a bare field dump.
    ok = (n > 0 and tiny == 0 and not_sentence == 0 and no_refs == 0
          and raw_json == 0 and no_kind == 0)
    record(conn, "rag_chunk_quality", "pass" if ok else "fail",
           f"{n} chunks, {tiny} under 30 chars, {not_sentence} not ending in a sentence "
           f"stop, {no_refs} without source refs, {raw_json} raw JSON dumps, "
           f"{no_kind} without a kind label")
    return ok


def check_license_coverage(conn) -> bool:
    total = conn.execute("select count(*) from anime").fetchone()[0]
    try:
        tiers = conn.execute("select count(*) from license_tiers").fetchone()[0]
        bad = conn.execute("select count(*) from license_tiers where tier not in "
                           "('cc0_only','permission_required','unresolved')").fetchone()[0]
    except Exception:
        record(conn, "license_tier_coverage", "fail", "license_tiers table missing")
        return False
    ok = tiers == total and bad == 0
    record(conn, "license_tier_coverage", "pass" if ok else "fail",
           f"{tiers}/{total} anime tiered, {bad} unknown tier values")
    return ok


def check_provenance_coverage(conn) -> bool:
    n_anime = conn.execute("select count(*) from anime").fetchone()[0]
    n_linked = conn.execute("select count(distinct anime_id) from anime_source").fetchone()[0]
    ok = n_anime > 0 and n_linked == n_anime
    record(conn, "provenance_coverage", "pass" if ok else "fail",
           f"{n_linked}/{n_anime} anime have at least one source link")
    return ok


def check_required_fields(conn) -> bool:
    missing = conn.execute(
        "select count(*) from anime where title_canonical is null and title_english is null").fetchone()[0]
    ok = missing == 0
    record(conn, "required_title_fields", "pass" if ok else "fail",
           f"{missing} anime without any title")
    return ok


# Upstream prose fields that must never reach a release artifact. The pipeline
# deletes them before writing; this list guards against a regression.
BANNED_EXPORT_KEYS = {
    "anime.jsonl": ("synopsis", "synopsis_source"),
    "characters.jsonl": ("description",),
    "episodes.jsonl": ("synopsis",),
    "themes.jsonl": ("description",),
    "genres.jsonl": ("description",),
}


def check_export_columns(conn) -> bool:
    from ..pipeline import export as export_mod
    export_dir = export_mod.EXPORT_DIR
    required = {
        "anime.jsonl": ("split", "license_tier", "genres", "studios"),
        "characters.jsonl": ("split", "license_tier"),
        "staff.jsonl": ("split", "license_tier"),
        "episodes.jsonl": ("split", "license_tier"),
        "relationships.jsonl": ("split", "license_tier"),
        "descriptions.jsonl": ("split", "license_tier"),
        "qa.jsonl": ("split", "license_tier"),
        "instructions.jsonl": ("split", "license_tier"),
        "rag_chunks.jsonl": ("split", "license_tier", "kind"),
    }
    table_of = {
        "anime.jsonl": "anime", "characters.jsonl": "characters", "staff.jsonl": "staff",
        "episodes.jsonl": "episodes", "relationships.jsonl": "relationships",
        "descriptions.jsonl": "descriptions", "qa.jsonl": "qa_pairs",
        "instructions.jsonl": "instructions", "rag_chunks.jsonl": "rag_chunks",
    }
    missing_files = []
    missing_cols = []
    empty_unexpected = []
    for name, cols in required.items():
        path = export_dir / name
        if not path.exists():
            missing_files.append(name)
            continue
        with open(path, encoding="utf-8") as fh:
            first = fh.readline()
        if not first:
            rows = conn.execute(f"select count(*) from {table_of[name]}").fetchone()[0]
            if rows:
                empty_unexpected.append(f"{name} ({rows:,} rows in {table_of[name]})")
            continue
        row = json.loads(first)
        absent = [c for c in cols if c not in row]
        if absent:
            missing_cols.append(f"{name}: {absent}")

    # Content policy: no upstream prose in any shipped artifact.
    banned_hits = []
    for name, keys in BANNED_EXPORT_KEYS.items():
        path = export_dir / name
        if not path.exists():
            continue
        blob = path.read_text(encoding="utf-8", errors="ignore")
        banned_hits.extend(f"{name}:{k}" for k in keys if f'"{k}":' in blob)
    prose_descriptions = conn.execute(
        "select count(*) from descriptions where kind<>'record_summary'").fetchone()[0]
    prose_chunks = conn.execute(
        "select count(*) from rag_chunks where kind='source_synopsis'").fetchone()[0]
    synopsis_qa = conn.execute(
        "select count(*) from qa_pairs where qtype='synopsis'").fetchone()[0]
    if prose_descriptions:
        banned_hits.append(f"descriptions.non_summary={prose_descriptions}")
    if prose_chunks:
        banned_hits.append(f"rag_chunks.source_synopsis={prose_chunks}")
    if synopsis_qa:
        banned_hits.append(f"qa_pairs.synopsis={synopsis_qa}")

    db_path = export_dir / "anime.db"
    if db_path.exists():
        conn.execute("ATTACH DATABASE ? AS exp", (str(db_path),))
        try:
            for table, col in (("anime", "synopsis"), ("anime", "synopsis_source"),
                               ("characters", "description"), ("episodes", "synopsis"),
                               ("themes", "description"), ("genres", "description")):
                n = conn.execute(
                    f"select count(*) from exp.{table} "
                    f"where {col} is not null and trim({col})<>''").fetchone()[0]
                if n:
                    banned_hits.append(f"anime.db:{table}.{col}={n}")
            n = conn.execute(
                "select count(*) from exp.descriptions "
                "where kind is null or kind<>'record_summary'").fetchone()[0]
            if n:
                banned_hits.append(f"anime.db:descriptions.non_summary={n}")
        finally:
            conn.execute("DETACH DATABASE exp")

    ok = not missing_files and not missing_cols and not empty_unexpected and not banned_hits
    record(conn, "export_schema", "pass" if ok else "fail",
           f"missing files={missing_files[:3]} missing columns={missing_cols[:5]} "
           f"empty despite source rows={empty_unexpected[:3]} upstream prose={banned_hits[:5]}")
    return ok


def run_validation() -> dict:
    cfg = load()
    conn = connect()
    conn.execute("DELETE FROM quality_validation")
    results = {
        "min_titles": check_min_titles(conn, cfg),
        "unique_source_ids": check_unique_source_ids(conn),
        "referential_integrity": check_no_orphans(conn),
        "no_duplicate_titles": check_no_duplicate_titles(conn),
        "enum_conformance": check_enum_domains(conn),
        "value_ranges": check_value_ranges(conn),
        "entity_duplicates": check_entity_duplicates(conn),
        "name_semantics": check_name_semantics(conn),
        "relationship_integrity": check_relationship_integrity(conn),
        "split_leakage": check_split_leakage(conn),
        "split_proportions": check_split_proportions(conn),
        "qa_grounding": check_qa_grounding(conn),
        "qa_fields_resolve": check_qa_field_resolution(conn),
        "qa_diversity": check_qa_diversity(conn),
        "instruction_grounding": check_instruction_grounding(conn),
        "instruction_diversity": check_instruction_diversity(conn),
        "rag_quality": check_rag_quality(conn),
        "license_coverage": check_license_coverage(conn),
        "provenance_coverage": check_provenance_coverage(conn),
        "required_fields": check_required_fields(conn),
        "export_schema": check_export_columns(conn),
    }
    failed = [k for k, v in results.items() if not v]
    status = "pass" if not failed else "fail"
    log(conn, "validate", f"{status}: {results}")
    conn.commit()
    conn.close()
    return {"status": status, "checks": results, "failed": failed}


def main(argv=None) -> int:
    res = run_validation()
    print(json.dumps(res, indent=2))
    return 0 if res["status"] == "pass" else 1
