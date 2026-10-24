"""Normalization, value repair, and entity deduplication.

Runs after collection/entity extraction and before the derived text stages.
Every step is idempotent so the stage can be re-run safely.

What it does:
  1. merges exact duplicate anime rows (normalized title + same year)
  2. canonicalizes enums (type, status, season, source material, age rating)
  3. repairs impossible values (score 0, year 0/out of range, negative counts)
  4. rescales Shikimori 0-10 scores onto the AniList 0-100 scale
  5. strips HTML and normalizes whitespace/Unicode in text fields
  6. canonicalizes relation names and merges duplicate relationship edges
  7. deduplicates alt titles, characters, staff, and episodes
  8. fixes the `name_native` field, which held Russian localizations
  9. merges the same person recorded by two sources into one row
"""

import json
import re
import unicodedata

from ..db import connect, cp_set, log

MAX_YEAR_AHEAD = 5
MIN_YEAR = 1900

TYPE_MAP = {
    "tv": "TV", "movie": "MOVIE", "ova": "OVA", "ona": "ONA",
    "special": "SPECIAL", "tv_special": "TV_SPECIAL", "tv_short": "TV_SHORT",
    "short": "SHORT", "ona_short": "ONA_SHORT", "music": "MUSIC",
    "pv": "PV", "cm": "CM", "web": "ONA", "unknown": None, "": None,
}

STATUS_MAP = {
    "finished": "FINISHED", "released": "FINISHED", "complete": "FINISHED",
    "completed": "FINISHED",
    "releasing": "RELEASING", "currently airing": "RELEASING", "current": "RELEASING",
    "airing": "RELEASING",
    "not yet released": "NOT_YET_RELEASED", "not_yet_released": "NOT_YET_RELEASED",
    "not yet aired": "NOT_YET_RELEASED", "unreleased": "NOT_YET_RELEASED",
    "tba": "NOT_YET_RELEASED", "anons": "NOT_YET_RELEASED", "upcoming": "NOT_YET_RELEASED",
    "cancelled": "CANCELLED", "canceled": "CANCELLED",
    "hiatus": "HIATUS", "on hiatus": "HIATUS",
}

SEASON_MAP = {"winter": "WINTER", "spring": "SPRING", "summer": "SUMMER", "fall": "FALL"}

SOURCE_MAP = {
    "manga": "MANGA", "original": "ORIGINAL", "other": "OTHER",
    "light_novel": "LIGHT_NOVEL", "light novel": "LIGHT_NOVEL",
    "visual_novel": "VISUAL_NOVEL", "visual novel": "VISUAL_NOVEL",
    "video_game": "VIDEO_GAME", "video game": "VIDEO_GAME", "game": "VIDEO_GAME",
    "novel": "NOVEL", "web_novel": "WEB_NOVEL", "web novel": "WEB_NOVEL",
    "doujinshi": "DOUJINSHI", "anime": "ANIME", "music": "MUSIC",
    "picture_book": "PICTURE_BOOK", "picture book": "PICTURE_BOOK",
    "4_koma_manga": "MANGA", "4-koma manga": "MANGA",
    "card_game": "CARD_GAME", "card game": "CARD_GAME",
    "web_manga": "WEB_MANGA", "web manga": "WEB_MANGA",
    "mixed_media": "MIXED_MEDIA", "mixed media": "MIXED_MEDIA",
    "radio": "RADIO", "book": "BOOK", "live_action": "LIVE_ACTION",
    "live action": "LIVE_ACTION", "unknown": None, "": None,
}

RELATION_MAP = {
    "sequel": "SEQUEL", "prequel": "PREQUEL",
    "parent": "PARENT_STORY", "parent story": "PARENT_STORY", "parent_story": "PARENT_STORY",
    "full story": "FULL_STORY", "full_story": "FULL_STORY",
    "side story": "SIDE_STORY", "side_story": "SIDE_STORY",
    "spin off": "SPIN_OFF", "spin_off": "SPIN_OFF", "spin-off": "SPIN_OFF", "spinoff": "SPIN_OFF",
    "alternative": "ALTERNATIVE", "alternative setting": "ALTERNATIVE_SETTING",
    "alternative_setting": "ALTERNATIVE_SETTING",
    "alternative version": "ALTERNATIVE_VERSION", "alternative_version": "ALTERNATIVE_VERSION",
    "character": "CHARACTER", "adaptation": "ADAPTATION", "summary": "SUMMARY",
    "other": "OTHER", "same series": "SAME_SERIES",
}

ROLE_MAP = {"main": "Main", "supporting": "Supporting", "background": "Background"}
ROLE_RANK = {"Main": 0, "Supporting": 1, "Background": 2}

AGE_MAP = {
    "g": "G", "pg": "PG", "pg_13": "PG-13", "pg-13": "PG-13",
    "r": "R", "r+": "R+", "r_plus": "R+", "r+17": "R+", "rx": "RX",
    "nc-17": "RX", "18+": "R+", "all ages": "G",
}

ALLOWED_TYPE = {"TV", "MOVIE", "OVA", "ONA", "SPECIAL", "TV_SPECIAL", "SHORT",
                "TV_SHORT", "ONA_SHORT", "MUSIC", "PV", "CM"}
ALLOWED_STATUS = {"FINISHED", "RELEASING", "NOT_YET_RELEASED", "CANCELLED", "HIATUS"}
ALLOWED_SEASON = {"WINTER", "SPRING", "SUMMER", "FALL"}
ALLOWED_SOURCE = {"ORIGINAL", "MANGA", "LIGHT_NOVEL", "NOVEL", "WEB_NOVEL", "WEB_MANGA",
                  "VISUAL_NOVEL", "VIDEO_GAME", "CARD_GAME", "GAME", "ANIME", "MUSIC",
                  "BOOK", "PICTURE_BOOK", "RADIO", "LIVE_ACTION", "MIXED_MEDIA",
                  "DOUJINSHI", "OTHER"}
ALLOWED_AGE = {"G", "PG", "PG-13", "R", "R+", "RX"}

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


def norm_text(value: str | None) -> str | None:
    """NFKC, collapse whitespace, trim. Returns None for empty strings."""
    if value is None:
        return None
    s = unicodedata.normalize("NFKC", str(value))
    s = s.replace("\u00ad", "").replace("\u200b", "")
    s = WS_RE.sub(" ", s).strip()
    return s or None


def strip_html(value: str | None) -> str | None:
    if not value:
        return None
    s = TAG_RE.sub(" ", str(value))
    s = (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
          .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)  # markdown links
    s = WS_RE.sub(" ", s).strip()
    return s or None


def norm_key(value: str | None) -> str:
    """Aggressive key used only for duplicate detection, never for display."""
    if not value:
        return ""
    s = unicodedata.normalize("NFKC", str(value)).casefold()
    return "".join(ch for ch in s if ch.isalnum())


def is_cyrillic(value: str | None) -> bool:
    if not value:
        return False
    # Any Cyrillic letter marks a Russian/localized name. A majority test missed
    # mixed labels such as "Шеф BKA" and "Рэд XIII", which then stayed in the
    # native-name field where consumers expect Japanese script.
    return any("\u0400" <= ch <= "\u04ff" for ch in value)


def ensure_column(conn, table: str, column: str, decl: str) -> None:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _reassign(conn, table: str, old: int, new: int) -> None:
    """Move child rows from `old` anime to `new`, dropping conflicting duplicates."""
    conn.execute(f"UPDATE OR IGNORE {table} SET anime_id=? WHERE anime_id=?", (new, old))
    conn.execute(f"DELETE FROM {table} WHERE anime_id=?", (old,))


def _merge_anime_row(conn, keep: int, drop: int) -> None:
    cols = ("title_canonical", "title_english", "title_japanese", "synopsis", "synopsis_source",
            "type", "status", "episodes", "duration_min", "aired_from", "aired_to", "season",
            "year", "mean_score", "popularity", "favourites", "source_material", "age_rating",
            "quality_tier", "confidence")
    row = conn.execute("select * from anime where anime_id=?", (drop,)).fetchone()
    if row is None:
        return
    cur = conn.execute("select * from anime where anime_id=?", (keep,)).fetchone()
    for col in cols:
        if cur[col] is None and row[col] is not None:
            conn.execute(f"update anime set {col}=? where anime_id=?", (row[col], keep))


def merge_duplicate_anime(conn) -> dict:
    """Merge anime rows that share a normalized title and the same release year."""
    rows = conn.execute(
        "select anime_id, title_canonical, title_english, year from anime "
        "where year is not null").fetchall()
    groups: dict[tuple[str, int], list[int]] = {}
    for r in rows:
        key = norm_key(r["title_canonical"] or r["title_english"])
        if not key:
            continue
        groups.setdefault((key, r["year"]), []).append(r["anime_id"])

    # Pairwise merge is enough: groups are almost always size 2, and after a merge
    # the surviving id absorbs the rest on the next pass of the loop.
    merged = 0
    clusters = 0
    for (key, year), ids in groups.items():
        if len(ids) < 2:
            continue
        ids = sorted(ids)
        keep = ids[0]
        clusters += 1
        for drop in ids[1:]:
            _merge_anime_row(conn, keep, drop)
            for table in ("anime_source", "alt_titles", "anime_genres", "anime_themes",
                          "anime_studios", "characters", "staff", "episodes", "relationships",
                          "descriptions", "splits", "franchises"):
                _reassign(conn, table, drop, keep)
            conn.execute("update provenance set entity_id=? where entity='anime' and entity_id=?",
                         (str(keep), str(drop)))
            conn.execute("delete from anime where anime_id=?", (drop,))
            merged += 1
        conn.execute(
            "INSERT INTO dedup_log(cluster_id,canonical_anime_id,method,members,created_at) "
            "VALUES(?,?,?,?,datetime('now'))",
            (900000 + clusters, keep, "normalized_title_year", json.dumps(ids)))
    conn.commit()
    return {"merged": merged, "clusters": clusters}


def normalize_anime(conn) -> dict:
    today_year = 2026
    max_year = today_year + MAX_YEAR_AHEAD
    changed = 0
    rows = conn.execute(
        "select anime_id, type, status, season, source_material, age_rating, year, mean_score, "
        "episodes, duration_min, popularity, favourites, aired_from, aired_to, title_canonical, "
        "title_english, title_japanese, synopsis from anime").fetchall()
    has_anilist = {r[0] for r in conn.execute(
        "select distinct anime_id from anime_source where source='anilist'")}
    for r in rows:
        aid = r["anime_id"]
        updates: dict[str, object] = {}

        v = TYPE_MAP.get((r["type"] or "").strip().lower(), r["type"])
        if v not in ALLOWED_TYPE:
            v = None
        if v != r["type"]:
            updates["type"] = v

        st = (r["status"] or "").strip().lower()
        v = STATUS_MAP.get(st, r["status"].upper() if r["status"] and r["status"].isupper() else r["status"])
        if v not in ALLOWED_STATUS:
            v = None
        if v != r["status"]:
            updates["status"] = v

        se = (r["season"] or "").strip().lower()
        v = SEASON_MAP.get(se)
        if v != r["season"]:
            updates["season"] = v

        raw_sm = (r["source_material"] or "").strip()
        sm = SOURCE_MAP.get(raw_sm.lower(), raw_sm.upper().replace(" ", "_") if raw_sm else None)
        if sm not in ALLOWED_SOURCE:
            sm = None
        if sm != r["source_material"]:
            updates["source_material"] = sm

        ar = (r["age_rating"] or "").strip().lower()
        v = AGE_MAP.get(ar) if ar else None
        if v not in ALLOWED_AGE:
            v = None
        if v != r["age_rating"]:
            updates["age_rating"] = v

        year = r["year"]
        if year is not None and not (MIN_YEAR <= year <= max_year):
            year = None
        if year is None:
            af = r["aired_from"]
            if af and DATE_RE.match(af):
                year = int(af[:4])
                if not (MIN_YEAR <= year <= max_year):
                    year = None
        if year != r["year"]:
            updates["year"] = year

        score = r["mean_score"]
        if score is not None:
            if score <= 0:
                score = None
            elif aid not in has_anilist and score <= 10:
                score = round(score * 10, 1)  # Shikimori 0-10 scale
            elif score > 100:
                score = None
        if score != r["mean_score"]:
            updates["mean_score"] = score

        for col in ("episodes", "duration_min", "popularity", "favourites"):
            val = r[col]
            if val is None:
                continue
            # A count of zero means "unknown" as often as it means "none": most
            # works with episodes=0 are unreleased or have no published count.
            if val < 0 or (col in ("episodes", "duration_min") and val == 0) \
                    or (col == "episodes" and val > 20000) or (col == "duration_min" and val > 1000):
                updates[col] = None

        for col in ("aired_from", "aired_to"):
            val = r[col]
            if val and not DATE_RE.match(val):
                updates[col] = None

        for col in ("title_canonical", "title_english", "title_japanese"):
            val = norm_text(r[col])
            if val != r[col]:
                updates[col] = val

        syn = strip_html(r["synopsis"])
        if syn != r["synopsis"]:
            updates["synopsis"] = syn

        if updates:
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"update anime set {sets} where anime_id=?", (*updates.values(), aid))
            changed += 1
    conn.execute("update anime set title_canonical=title_english "
                 "where (title_canonical is null or title_canonical='') and title_english is not null")
    conn.commit()
    return {"anime_rows_changed": changed}


def normalize_alt_titles(conn) -> dict:
    ensure_column(conn, "alt_titles", "sources", "TEXT")
    before = conn.execute("select count(*) from alt_titles").fetchone()[0]
    conn.execute("delete from alt_titles where title is null or trim(title)=''")
    rows = conn.execute(
        "select rowid, anime_id, source, lang, kind, title from alt_titles").fetchall()
    groups: dict[tuple[int, str], dict] = {}
    drop: list[int] = []
    for r in rows:
        key = (r["anime_id"], norm_key(r["title"]))
        if not key[1]:
            drop.append(r["rowid"])
            continue
        if key in groups:
            g = groups[key]
            g["sources"].add(r["source"])
            if not g["lang"] and r["lang"]:
                g["lang"] = r["lang"]
            if not g["kind"] and r["kind"]:
                g["kind"] = r["kind"]
            drop.append(r["rowid"])
        else:
            groups[key] = {"rowid": r["rowid"], "title": norm_text(r["title"]),
                           "lang": r["lang"], "kind": r["kind"], "sources": {r["source"]}}
    conn.executemany("delete from alt_titles where rowid=?", [(i,) for i in drop])
    for g in groups.values():
        conn.execute("update alt_titles set title=?, lang=?, kind=?, sources=? where rowid=?",
                     (g["title"], g["lang"], g["kind"],
                      json.dumps(sorted(g["sources"]), ensure_ascii=False), g["rowid"]))
    after = conn.execute("select count(*) from alt_titles").fetchone()[0]
    conn.commit()
    return {"alt_titles_before": before, "alt_titles_after": after, "removed": before - after}


def normalize_relationships(conn) -> dict:
    before = conn.execute("select count(*) from relationships").fetchone()[0]
    conn.execute("delete from relationships where other_anime_id is null "
                 "or other_anime_id=anime_id")
    rows = conn.execute(
        "select rowid, anime_id, other_anime_id, relation, source from relationships").fetchall()
    groups: dict[tuple[int, int, str], dict] = {}
    drop: list[int] = []
    for r in rows:
        rel = RELATION_MAP.get((r["relation"] or "").strip().lower(),
                               (r["relation"] or "OTHER").strip().upper().replace(" ", "_"))
        key = (r["anime_id"], r["other_anime_id"], rel)
        if key in groups:
            g = groups[key]
            g["sources"].add(r["source"])
            drop.append(r["rowid"])
        else:
            groups[key] = {"rowid": r["rowid"], "rel": rel, "sources": {r["source"]}}
    conn.executemany("delete from relationships where rowid=?", [(i,) for i in drop])
    for key, g in groups.items():
        conn.execute("update relationships set relation=?, source=? where rowid=?",
                     (g["rel"], "+".join(sorted(g["sources"])), g["rowid"]))
    after = conn.execute("select count(*) from relationships").fetchone()[0]
    conn.commit()
    return {"relationships_before": before, "relationships_after": after,
            "removed": before - after}


def _parse_json_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return [str(value).strip()] if str(value).strip() else []
    if isinstance(parsed, list):
        return [str(v).strip() for v in parsed if str(v).strip()]
    return [str(parsed).strip()]


def _parse_refs(value) -> list[dict]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [{"source": r["source"], "remote_id": str(r["remote_id"])}
            for r in parsed
            if isinstance(r, dict) and r.get("source") and r.get("remote_id") is not None]


def _merge_refs(refs: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for ref in refs:
        key = (ref["source"], ref["remote_id"])
        if key not in seen:
            seen.add(key)
            out.append(ref)
    return out


def normalize_characters(conn) -> dict:
    ensure_column(conn, "characters", "name_ru", "TEXT")
    ensure_column(conn, "characters", "source_refs", "TEXT")
    before = conn.execute("select count(*) from characters").fetchone()[0]

    rows = conn.execute(
        "select id, anime_id, source, remote_id, name, name_native, name_ru, role, description, "
        "voice_actors, source_refs from characters").fetchall()
    by_key: dict[tuple[int, str], dict] = {}
    drop: list[int] = []
    updates: list[tuple] = []
    for r in rows:
        roles = _parse_json_list(r["role"])
        native = norm_text(r["name_native"])
        ru = norm_text(r["name_ru"])
        if native and is_cyrillic(native):
            ru = ru or native
            native = None
        name = norm_text(r["name"])
        vas = _parse_json_list(r["voice_actors"])
        key = (r["anime_id"], norm_key(name))
        refs = _parse_refs(r["source_refs"]) or [
            {"source": r["source"], "remote_id": r["remote_id"]}]
        if key[1] and key in by_key:
            g = by_key[key]
            g["roles"].update(roles)
            g["vas"].update(vas)
            g["refs"].extend(refs)
            g["description"] = g["description"] or r["description"]
            g["name_ru"] = g["name_ru"] or ru
            g["name_native"] = g["name_native"] or native
            drop.append(r["id"])
        else:
            entry = {"id": r["id"], "name": name, "name_native": native, "name_ru": ru,
                     "roles": set(roles), "vas": set(vas), "refs": refs,
                     "description": r["description"]}
            if key[1]:
                by_key[key] = entry
            updates.append(entry)
    conn.executemany("delete from characters where id=?", [(i,) for i in drop])

    for e in updates:
        # Roles are merged across sources; the strongest one wins so a character
        # listed as Main by one source and Background by another stays Main.
        roles = sorted((ROLE_MAP[r.lower()] for r in e["roles"]
                        if r.lower() in ROLE_MAP), key=lambda x: ROLE_RANK[x])
        role = roles[0] if roles else None
        vas = [{"name": v} for v in sorted(e["vas"])]
        conn.execute(
            "update characters set name=?, name_native=?, name_ru=?, role=?, description=?, "
            "voice_actors=?, source_refs=? where id=?",
            (e["name"], e["name_native"], e["name_ru"], role,
             strip_html(e["description"]),
             json.dumps(vas, ensure_ascii=False) if vas else None,
             json.dumps(_merge_refs(e["refs"]), ensure_ascii=False), e["id"]))
    conn.commit()
    after = conn.execute("select count(*) from characters").fetchone()[0]
    desc = conn.execute("select count(*) from characters where description is not null").fetchone()[0]
    vas = conn.execute("select count(*) from characters where voice_actors is not null").fetchone()[0]
    return {"characters_before": before, "characters_after": after,
            "removed": before - after, "with_description": desc, "with_voice_actors": vas}


def normalize_staff(conn) -> dict:
    ensure_column(conn, "staff", "name_ru", "TEXT")
    ensure_column(conn, "staff", "source_refs", "TEXT")
    before = conn.execute("select count(*) from staff").fetchone()[0]
    rows = conn.execute(
        "select id, anime_id, source, remote_id, name, name_native, name_ru, roles, "
        "source_refs from staff").fetchall()
    by_key: dict[tuple[int, str], dict] = {}
    drop: list[int] = []
    entries: list[dict] = []
    for r in rows:
        roles = _parse_json_list(r["roles"])
        native = norm_text(r["name_native"])
        ru = norm_text(r["name_ru"])
        if native and is_cyrillic(native):
            ru = ru or native
            native = None
        name = norm_text(r["name"])
        key = (r["anime_id"], norm_key(name))
        refs = _parse_refs(r["source_refs"]) or [
            {"source": r["source"], "remote_id": r["remote_id"]}]
        if key[1] and key in by_key:
            g = by_key[key]
            g["roles"].update(roles)
            g["refs"].extend(refs)
            g["name_ru"] = g["name_ru"] or ru
            g["name_native"] = g["name_native"] or native
            drop.append(r["id"])
        else:
            e = {"id": r["id"], "name": name, "name_native": native, "name_ru": ru,
                 "roles": set(roles), "refs": refs}
            if key[1]:
                by_key[key] = e
            entries.append(e)
    conn.executemany("delete from staff where id=?", [(i,) for i in drop])
    for e in entries:
        conn.execute(
            "update staff set name=?, name_native=?, name_ru=?, roles=?, source_refs=? where id=?",
            (e["name"], e["name_native"], e["name_ru"],
             json.dumps(sorted(e["roles"]), ensure_ascii=False),
             json.dumps(_merge_refs(e["refs"]), ensure_ascii=False), e["id"]))
    conn.commit()
    after = conn.execute("select count(*) from staff").fetchone()[0]
    return {"staff_before": before, "staff_after": after, "removed": before - after}


def normalize_episodes(conn) -> dict:
    before = conn.execute("select count(*) from episodes").fetchone()[0]
    conn.execute("delete from episodes where number is null or number < 0")
    rows = conn.execute(
        "select id, anime_id, number, title, synopsis from episodes").fetchall()
    best: dict[tuple[int, int], tuple[int, int]] = {}
    drop: list[int] = []
    for r in rows:
        key = (r["anime_id"], r["number"])
        richness = (1 if r["title"] else 0) + (1 if r["synopsis"] else 0)
        if key in best:
            prev_id, prev_rich = best[key]
            if richness > prev_rich:
                drop.append(prev_id)
                best[key] = (r["id"], richness)
            else:
                drop.append(r["id"])
        else:
            best[key] = (r["id"], richness)
    conn.executemany("delete from episodes where id=?", [(i,) for i in drop])
    for r in conn.execute("select id, title, synopsis from episodes").fetchall():
        conn.execute("update episodes set title=?, synopsis=? where id=?",
                     (norm_text(r["title"]), strip_html(r["synopsis"]), r["id"]))
    conn.commit()
    after = conn.execute("select count(*) from episodes").fetchone()[0]
    return {"episodes_before": before, "episodes_after": after, "removed": before - after}


def _dedupe_lookup(conn, table: str, key: str, extras: tuple[str, ...] = ()) -> int:
    """Trim a natural key and merge rows that collide after trimming.

    The lookup tables key on the label itself, so an `update ... set key=trim(key)`
    can hit the primary key when both "X" and "X " exist. Keep the richest row of
    each group, delete the rest, then write the trimmed key.
    """
    select_extra = ", ".join(extras) if extras else "NULL"
    rows = conn.execute(
        f"select rowid, {key}, {select_extra} from {table}").fetchall()
    best: dict[str, tuple[int, int]] = {}
    drop: list[int] = []
    for row in rows:
        rid, raw = row[0], row[1]
        clean = (raw or "").strip()
        if not clean:
            drop.append(rid)
            continue
        richness = sum(1 for v in row[2:] if v)
        prev = best.get(clean)
        if prev is None:
            best[clean] = (richness, rid)
        elif richness > prev[0]:
            drop.append(prev[1])
            best[clean] = (richness, rid)
        else:
            drop.append(rid)
    conn.executemany(f"delete from {table} where rowid=?", [(i,) for i in drop])
    for clean, (_, rid) in best.items():
        conn.execute(f"update {table} set {key}=? where rowid=?", (clean, rid))
    return len(drop)


def normalize_reference_tables(conn) -> dict:
    removed = {
        "genres": _dedupe_lookup(conn, "genres", "genre", ("description",)),
        "themes": _dedupe_lookup(conn, "themes", "theme", ("description",)),
        "studios": _dedupe_lookup(conn, "studios", "studio_name",
                                  ("source_studio_id", "url")),
    }
    conn.commit()
    return {
        "genres": conn.execute("select count(*) from genres").fetchone()[0],
        "themes": conn.execute("select count(*) from themes").fetchone()[0],
        "studios": conn.execute("select count(*) from studios").fetchone()[0],
        "merged": removed,
    }


def run() -> int:
    conn = connect()
    result = {}
    result["anime_duplicates"] = merge_duplicate_anime(conn)
    result["anime_fields"] = normalize_anime(conn)
    result["alt_titles"] = normalize_alt_titles(conn)
    result["relationships"] = normalize_relationships(conn)
    result["characters"] = normalize_characters(conn)
    result["staff"] = normalize_staff(conn)
    result["episodes"] = normalize_episodes(conn)
    result["reference"] = normalize_reference_tables(conn)
    conn.execute("delete from quality_validation")
    cp_set(conn, "normalize_done", True)
    log(conn, "normalize", json.dumps(result, ensure_ascii=False))
    print(json.dumps(result, indent=2))
    conn.close()
    return 0
