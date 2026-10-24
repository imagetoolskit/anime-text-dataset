"""Backfill: fill missing canonical scalar fields from already-fetched source
payloads, with no network calls.

The dedup pass canonicalizes works but only the depth tier (~top 20%) is
enriched with detail. Discovery payloads (AniList media_light, Kitsu anime,
Shikimori anime, Wikidata items) already sit in `raw_payload` for tens of
thousands of works and carry year, status, episode counts, runtimes, seasons,
age ratings, synopses, scores, popularity and English titles. This phase merges
them into the canonical `anime` rows, filling only fields that are currently
missing, with a fixed source priority (anilist > kitsu > shikimori > wikidata).

Backfills are recorded in per-entity `provenance` rows so every value stays
attributable.

Usage:
    python -m src.cli backfill
"""
from __future__ import annotations

import html
import json
import re

from ..db import connect, cp_set, log

_TAG_RE = re.compile(r"<[^>]+>")


def clean_html(value):
    if not value:
        return None
    out = _TAG_RE.sub(" ", str(value))
    out = html.unescape(out).replace("\u3000", " ")
    out = " ".join(out.split())
    return out or None


def _date(d):
    if not isinstance(d, dict):
        return None
    y, m, dd = d.get("year"), d.get("month"), d.get("day")
    if not y:
        return None
    return f"{int(y):04d}-{int(m or 1):02d}-{int(dd or 1):02d}"


def _dstr(value):
    if not value:
        return None
    value = str(value).strip()
    return value[:10] if len(value) >= 10 else None


def _year_of(value):
    if not value:
        return None
    s = str(value)
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    return None


def _float100(value):
    n = _num(value)
    if n is None:
        return None
    return int(round(n))


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _shiki_status(v):
    if not v:
        return None
    return {"latest": "releasing", "ongoing": "releasing"}.get(v, str(v).lower())


def _season(v):
    if not v:
        return None
    s = str(v).lower()
    if "_" in s:
        return s.split("_")[0]
    return s


def _age_rating(v):
    if not v:
        return None
    return {"g": "G", "pg": "PG", "pg_13": "PG-13", "r": "R",
            "r_plus": "R+", "rx": "R18+"}.get(str(v).lower(), str(v))


def _from_anilist(p):
    ttl = p.get("title") or {}
    start = p.get("startDate") or {}
    end = p.get("endDate") or {}
    return {
        "type": (p.get("format") or "").lower(),
        "status": p.get("status"),
        "episodes": p.get("episodes"),
        "duration_min": p.get("duration"),
        "aired_from": _date(start),
        "aired_to": _date(end),
        "season": (p.get("season") or "").lower() or None,
        "year": start.get("year") or p.get("seasonYear"),
        "title_english": ttl.get("english"),
        "title_japanese": ttl.get("native"),
        "synopsis": clean_html(p.get("description") or p.get("summary")),
        "mean_score": p.get("averageScore"),
        "popularity": p.get("popularity"),
        "favourites": p.get("favourites"),
        "source_material": (p.get("source") or "").lower() or None,
        "age_rating": p.get("ageRating"),
    }


def _from_kitsu(payload):
    p = payload.get("attributes") or {}
    ttl = p.get("titles") or {}
    return {
        "type": (p.get("subtype") or "").lower(),
        "status": p.get("status"),
        "episodes": p.get("episodeCount"),
        "duration_min": p.get("episodeLength"),
        "aired_from": _dstr(p.get("startDate")),
        "aired_to": _dstr(p.get("endDate")),
        "season": None,
        "year": _year_of(p.get("startDate")),
        "title_english": ttl.get("en") or p.get("canonicalTitle"),
        "title_japanese": ttl.get("ja_jp") or ttl.get("ja") or ttl.get("ja_en"),
        "synopsis": clean_html(p.get("synopsis")),
        "mean_score": _float100(p.get("averageRating")),
        "popularity": p.get("popularityRank"),
        "favourites": None,
        "source_material": None,
        "age_rating": p.get("ageRating"),
    }


def _from_shikimori(p):
    en = p.get("english") or []
    return {
        "type": (p.get("kind") or "").lower(),
        "status": _shiki_status(p.get("status")),
        "episodes": p.get("episodes"),
        "duration_min": (int(round(p["duration"] / 60))
                         if isinstance(p.get("duration"), (int, float)) and p["duration"] else None),
        "aired_from": _dstr(p.get("aired_on")),
        "aired_to": _dstr(p.get("released_on")),
        "season": _season(p.get("season")),
        "year": _year_of(p.get("aired_on")),
        "title_english": (en[0] if en else None),
        "title_japanese": p.get("name"),
        "synopsis": clean_html(p.get("description_html") or p.get("description")),
        "mean_score": _float100(_num(p.get("score")) * 10)
        if _num(p.get("score")) is not None else None,
        "popularity": p.get("popularity"),
        "favourites": None,
        "source_material": None,
        "age_rating": _age_rating(p.get("rating")),
    }


EMPTY = {
    "type": None, "status": None, "episodes": None, "duration_min": None,
    "aired_from": None, "aired_to": None, "season": None, "year": None,
    "title_english": None, "title_japanese": None, "synopsis": None,
    "mean_score": None, "popularity": None, "favourites": None,
    "source_material": None, "age_rating": None,
}

FIELDS = list(EMPTY)

SRC_PRIORITY = ["anilist", "kitsu", "shikimori", "wikidata"]


def _extract(source, payload):
    if not isinstance(payload, dict):
        return dict(EMPTY)
    if source == "anilist":
        out = _from_anilist(payload)
    elif source == "kitsu":
        out = _from_kitsu(payload)
    elif source == "shikimori":
        out = _from_shikimori(payload)
    else:  # wikidata
        year = None
        sd = payload.get("startDate")
        if isinstance(sd, dict):
            year = _year_of(sd.get("value"))
        out = {"type": None, "status": None, "episodes": None, "duration_min": None,
               "aired_from": None, "aired_to": None, "season": None, "year": year,
               "title_english": None, "title_japanese": None, "synopsis": None,
               "mean_score": None, "popularity": None, "favourites": None,
               "source_material": None, "age_rating": None}
    return {k: (v if v not in (None, "", 0) else None) for k, v in out.items()}


def _is_missing(current, field):
    if current is None:
        return True
    if isinstance(current, str):
        return not current.strip()
    if isinstance(current, (int, float)):
        return current == 0
    return False


def run() -> int:
    conn = connect()
    payloads = {}
    cur = conn.execute(
        "select source, remote_id, payload, license_note, retrieved_at, url from raw_payload"
    )
    for row in cur:
        try:
            data = json.loads(row["payload"])
        except (TypeError, json.JSONDecodeError):
            continue
        key = (row["source"], str(row["remote_id"]))
        if row["source"] in ("anilist", "kitsu", "shikimori", "wikidata"):
            payloads[key] = (_extract(row["source"], data), row["license_note"],
                             row["retrieved_at"], row["url"])

    links = {}
    for r in conn.execute("select anime_id, source, remote_id from anime_source"):
        links.setdefault(r["anime_id"], []).append((r["source"], str(r["remote_id"])))

    col_names = [d["name"] for d in conn.execute("pragma table_info(anime)")]
    rows = [dict(zip(col_names, row)) for row in conn.execute("select * from anime")]

    filled_total = 0
    n_backfilled = 0
    pending_prov = []

    for current in rows:
        aid = current["anime_id"]
        changes = {}
        src_used = {}
        for src in SRC_PRIORITY:
            for link_src, rid in links.get(aid, []):
                if link_src != src:
                    continue
                info = payloads.get((src, rid))
                if not info:
                    break
                ext = info[0]
                for field in FIELDS:
                    if field in changes:
                        continue
                    if _is_missing(current.get(field), field):
                        val = ext.get(field)
                        if val is not None:
                            changes[field] = val
                            src_used[field] = (src, info[1], info[2], info[3])
                            if field == "synopsis":
                                changes["synopsis_source"] = src
                                src_used["synopsis_source"] = (src, info[1], info[2], info[3])
                break
        if not changes:
            continue
        cols = ", ".join(f"{f}=?" for f in changes)
        conn.execute(
            f"UPDATE anime SET {cols} WHERE anime_id=?",
            tuple(changes.values()) + (aid,),
        )
        filled_total += len(changes)
        n_backfilled += 1
        by_source = {}
        for f in changes:
            by_source.setdefault(src_used[f][0], []).append(f)
        for src, fields in by_source.items():
            first = fields[0]
            note = (f"backfilled fields {','.join(fields)} for {src}; "
                    f"{src_used[first][1] or ''}").strip()
            pending_prov.append((aid, src, src_used[first][3], src_used[first][2], note))
        if n_backfilled % 1000 == 0:
            conn.commit()
            _flush_prov(conn, pending_prov)
            pending_prov = []
    conn.commit()
    if pending_prov:
        _flush_prov(conn, pending_prov)
    cp_set(conn, "backfill_done", True)
    log(conn, "backfill", f"backfilled {n_backfilled} anime rows, {filled_total} fields")
    print(json.dumps({"backfilled_anime": n_backfilled, "fields_filled": filled_total}))
    conn.close()
    return 0


def _flush_prov(conn, rows):
    if not rows:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO provenance(entity,entity_id,source,url,retrieved_at,license_note,confidence) "
        "VALUES('anime',?,?,?,?,?,0.7)", rows)


def main(argv=None) -> int:
    return run()