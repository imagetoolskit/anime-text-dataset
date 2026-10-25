"""Descriptions, both project-authored and upstream.

Two kinds are stored:

``record_summary``
    A short prose summary assembled only from structured fields already in the
    database (type, year, studio, episode count, genres, themes, cast, staff,
    source material). No plot detail is invented. This text is project-authored
    and covered by the repository's CC-BY-4.0 grant.

``source_synopsis``
    The upstream synopsis exactly as retrieved, with its source recorded in the
    ``source`` column. This is third-party expression: it is retained for
    completeness and is **excluded** from the project's CC-BY grant. The
    applicable owner and terms are listed in ``exports/attribution.json``.

Three sentence orderings are used for the generated summaries so the corpus
does not read as one template.
"""

import json
import zlib

from ..db import connect, cp_set, log
from .facts import DIRECTOR_EXCLUDE, find_staff

TYPE_LABEL = {
    "TV": "TV series", "MOVIE": "anime film", "OVA": "OVA", "ONA": "ONA",
    "SPECIAL": "TV special", "TV_SPECIAL": "TV special", "SHORT": "short",
    "TV_SHORT": "short TV series", "ONA_SHORT": "short ONA",
    "MUSIC": "music video", "PV": "promotional video", "CM": "commercial",
}

SOURCE_LABEL = {
    "MANGA": "a manga", "LIGHT_NOVEL": "a light novel", "NOVEL": "a novel",
    "WEB_NOVEL": "a web novel", "WEB_MANGA": "a web manga",
    "VISUAL_NOVEL": "a visual novel", "VIDEO_GAME": "a video game",
    "CARD_GAME": "a card game", "GAME": "a game", "ANIME": "an earlier anime",
    "MUSIC": "a music release", "BOOK": "a book", "PICTURE_BOOK": "a picture book",
    "RADIO": "a radio program", "LIVE_ACTION": "a live-action work",
    "MIXED_MEDIA": "a mixed-media project", "DOUJINSHI": "a doujinshi",
    "OTHER": "other source material",
}


def _join(items, conj="and"):
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return f"{', '.join(items[:-1])}, {conj} {items[-1]}"


def _year_clause(row) -> str | None:
    if row["aired_from"] and len(row["aired_from"]) >= 4:
        return row["aired_from"][:4]
    return str(row["year"]) if row["year"] else None


def build_description(row, genres, themes, studios, directors, cast) -> str | None:
    title = row["title_canonical"] or row["title_english"]
    if not title:
        return None
    kind = TYPE_LABEL.get(row["type"] or "", "anime work")
    year = _year_clause(row)
    n_eps = row["episodes"]
    studio = _join(studios[:2])
    genre_text = _join(genres[:4])
    theme_text = _join(themes[:3])
    director_text = _join(directors[:2])
    cast_text = _join(cast[:4])
    source = SOURCE_LABEL.get(row["source_material"] or "")

    opening = f"{title} is a {kind}"
    if year:
        opening += f" from {year}"
    opening += "."

    facts = []
    if n_eps and n_eps > 0:
        facts.append(f"It consists of {n_eps} episode{'s' if n_eps != 1 else ''}.")
    if studio:
        facts.append(f"The animation was produced by {studio}.")
    if director_text:
        facts.append(f"It was directed by {director_text}.")
    if source:
        facts.append(f"It adapts {source}.")
    if row["source_material"] == "ORIGINAL":
        facts.append("It is an original work rather than an adaptation.")

    detail = []
    if genre_text:
        detail.append(f"Its genres include {genre_text}.")
    if theme_text:
        detail.append(f"Recurring themes include {theme_text}.")
    if cast_text:
        detail.append(f"The main cast includes {cast_text}.")
    if row["mean_score"]:
        detail.append(f"Its recorded mean score is {float(row['mean_score']):.1f} out of 100.")

    blocks = [opening, " ".join(facts), " ".join(detail)]
    blocks = [b for b in blocks if b.strip()]
    if not blocks:
        return None
    # Rotate the middle and closing blocks so sentence order varies by record.
    if len(blocks) == 3 and zlib.crc32(str(row["anime_id"]).encode()) % 2:
        blocks = [blocks[0], blocks[2], blocks[1]]
    return " ".join(blocks)


def run() -> int:
    conn = connect()
    from .attribution import normalize_source
    from .normalize import ensure_column

    ensure_column(conn, "descriptions", "source", "TEXT")
    ensure_column(conn, "themes", "description_source", "TEXT")
    # Theme descriptions are inserted from AniList tags in `entities.py`.
    # Backfill the source for rows that predate the column.
    conn.execute(
        "UPDATE themes SET description_source='anilist' "
        "WHERE description IS NOT NULL AND trim(description)<>'' "
        "AND (description_source IS NULL OR description_source='')")
    # Rebuild upstream synopsis rows from the working `anime` table so the
    # source label and the text cannot drift apart.
    conn.execute("DELETE FROM descriptions WHERE kind='source_synopsis'")
    n = 0
    cur = conn.execute("select * from anime where title_canonical is not null or title_english is not null")
    for row in cur:
        aid = row["anime_id"]
        genres = [g[0] for g in conn.execute(
            "select genre from anime_genres where anime_id=? order by genre", (aid,))]
        themes = [t[0] for t in conn.execute(
            "select theme from anime_themes where anime_id=? order by theme", (aid,))]
        studios = [s[0] for s in conn.execute(
            "select studio_name from anime_studios where anime_id=? "
            "order by is_main desc, studio_name", (aid,))]
        staff_rows = conn.execute(
            "select name, roles from staff where anime_id=? order by id", (aid,)).fetchall()
        staff = []
        for r in staff_rows:
            try:
                parsed = json.loads(r["roles"] or "[]")
            except (TypeError, json.JSONDecodeError):
                parsed = []
            staff.append({"name": r["name"], "roles": parsed})
        directors = find_staff(staff, ("director",), DIRECTOR_EXCLUDE)[:2]
        cast = [c[0] for c in conn.execute(
            "select name from characters where anime_id=? and role='Main' "
            "group by name order by min(id) limit 4", (aid,))]
        text = build_description(row, genres, themes, studios, directors, cast)
        if text:
            conn.execute(
                "INSERT OR REPLACE INTO descriptions(anime_id,kind,text,synthetic,provenance) "
                "VALUES(?,?,?,?,?)",
                (aid, "record_summary", text, 1,
                 "generated from structured fields only; no plot facts invented"))
            n += 1

    upstream = 0
    for r in conn.execute(
        "select anime_id, synopsis, synopsis_source from anime "
        "where synopsis is not null and trim(synopsis)<>''"
    ):
        conn.execute(
            "INSERT OR REPLACE INTO descriptions"
            "(anime_id,kind,text,synthetic,provenance,source) VALUES(?,?,?,?,?,?)",
            (r["anime_id"], "source_synopsis", r["synopsis"], 0,
             "upstream synopsis; third-party text; see exports/attribution.json",
             normalize_source(r["synopsis_source"])))
        upstream += 1

    conn.commit()
    cp_set(conn, "descriptions_done", True)
    log(conn, "descriptions", f"record_summary={n} source_synopsis={upstream}")
    print(f"record_summaries={n} source_synopses={upstream}")
    conn.close()
    return 0
