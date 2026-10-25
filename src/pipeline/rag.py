"""Retrieval chunks.

Chunks are written as prose, not JSON dumps, because a retriever returns text
that a reader (or a model) has to understand on its own. Every chunk carries
`source_refs` pointing at the upstream records it was assembled from.

Chunk families per anime:
  record_summary   the generated record summary
  title_aliases    title, format, year, studios, genres, themes, aliases
  characters       main and supporting cast
  voice_cast       character-to-voice-actor pairs
  staff            production credits grouped by role
  episodes         the episode list
  relations        sequels, prequels, side stories, franchise neighbours
  source_synopsis  the upstream synopsis, kept verbatim and attributed

`source_synopsis` is third-party text. It carries a `prose_source` and is
excluded from the project's CC-BY-4.0 grant; see `exports/attribution.json`.
"""

import json

from ..db import connect, cp_set, log
from .attribution import normalize_source
from .facts import (DIRECTOR_EXCLUDE, MUSIC_EXCLUDE, WRITER_EXCLUDE, find_staff,
                    load_children, load_titles)

def _join(items, conj="and") -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return f"{', '.join(items[:-1])}, {conj} {items[-1]}"


def _caps(names: list[str], size: int = 40) -> list[list[str]]:
    return [names[i:i + size] for i in range(0, len(names), size)] or []


def build_chunks(title, row, children, refs, franchise_titles) -> list[tuple[str, str, list[str]]]:
    """Return (kind, text, referenced fields) tuples for one anime."""
    aid = row["anime_id"]
    out: list[tuple[str, str, list[str]]] = []

    genres = children["genres"].get(aid, [])
    themes = children["themes"].get(aid, [])
    studios = children["studios"].get(aid, [])
    chars = children["chars"].get(aid, [])
    staff = children["staff"].get(aid, [])
    episodes = children["episodes"].get(aid, [])
    relations = children["relations"].get(aid, [])

    if row["summary"]:
        out.append(("record_summary", row["summary"], ["descriptions.record_summary"]))

    if row.get("synopsis"):
        out.append(("source_synopsis", row["synopsis"], ["anime.synopsis"]))

    aliases = [a["title"] for a in children["alts"].get(aid, []) if a["title"] != title][:8]
    lead = f"{title} is an anime work"
    if row["type"]:
        lead = f"{title} is a {row['type'].replace('_', ' ').lower()} anime work"
    if row["year"]:
        lead += f" from {row['year']}"
    lead += "."
    detail = []
    if studios:
        detail.append(f"The animation was produced by {_join(studios[:3])}.")
    if genres:
        detail.append(f"Its genres are {_join(genres[:5])}.")
    if themes:
        detail.append(f"It explores themes such as {_join(themes[:5])}.")
    if aliases:
        detail.append(f"It is also known as {_join(aliases)}.")
    if detail:
        out.append(("title_aliases", " ".join([lead] + detail), ["anime", "alt_titles",
                                                                 "genres", "themes", "studios"]))

    if chars:
        main = [c["name"] for c in chars if c["role"] == "Main"]
        supporting = [c["name"] for c in chars if c["role"] == "Supporting"]
        other = [c["name"] for c in chars if c["role"] not in ("Main", "Supporting")]
        for group, label in ((main, "main characters"), (supporting, "supporting characters"),
                             (other, "further characters")):
            for part in _caps(group):
                text = f"{title} — {label}: {_join(part)}."
                out.append(("characters", text, ["characters"]))
        voiced = [f"{c['name']} is voiced by {c['va']}" for c in chars if c["va"]][:30]
        if voiced:
            out.append(("voice_cast", f"Voice cast for {title}: " + "; ".join(voiced) + ".",
                        ["characters.voice_actors"]))

    if staff:
        roles: list[str] = []
        directors = find_staff(staff, ("director",), DIRECTOR_EXCLUDE)
        if directors:
            roles.append(f"Direction: {_join(directors[:3])}")
        composers = find_staff(staff, ("music", "composer"), MUSIC_EXCLUDE)
        if composers:
            roles.append(f"Music: {_join(composers[:3])}")
        writers = find_staff(staff, ("series composition", "script", "screenplay"),
                             WRITER_EXCLUDE)
        if writers:
            roles.append(f"Script: {_join(writers[:3])}")
        by_role: dict[str, list[str]] = {}
        for member in staff:
            for role in member["roles"][:2]:
                if role:
                    by_role.setdefault(role, []).append(member["name"])
        for role in sorted(by_role)[:20]:
            if any(role.startswith(r.split(":")[0]) for r in roles):
                continue
            names = list(dict.fromkeys(by_role[role]))[:5]
            roles.append(f"{role}: {_join(names)}")
        for part in [roles[i:i + 12] for i in range(0, len(roles), 12)]:
            out.append(("staff", f"Production credits for {title}. " + "; ".join(part) + ".",
                        ["staff"]))

    if episodes:
        for part in [episodes[i:i + 30] for i in range(0, len(episodes), 30)]:
            listing = "; ".join(f"episode {e['number']} is titled \"{e['title']}\"" for e in part)
            out.append(("episodes", f"Episode list for {title}: {listing}.", ["episodes"]))

    if relations:
        by_rel: dict[str, list[str]] = {}
        for r in relations:
            if r["other"] not in franchise_titles:
                continue
            by_rel.setdefault(r["relation"], []).append(franchise_titles[r["other"]])
        for rel in sorted(by_rel):
            names = list(dict.fromkeys(by_rel[rel]))[:8]
            out.append(("relations",
                        f"{title} has these {rel.lower().replace('_', ' ')} links: {_join(names)}.",
                        ["relationships"]))

    return out


def source_refs(conn) -> dict[int, list[dict]]:
    refs: dict[int, list[dict]] = {}
    for r in conn.execute("select anime_id, source, remote_id, url from anime_source"):
        entry = {"source": r["source"], "remote_id": r["remote_id"]}
        if r["url"]:
            entry["url"] = r["url"]
        refs.setdefault(r["anime_id"], []).append(entry)
    return refs


def run() -> int:
    conn = connect()
    from .normalize import ensure_column
    ensure_column(conn, "rag_chunks", "kind", "TEXT")
    ensure_column(conn, "rag_chunks", "prose_source", "TEXT")
    conn.execute("DELETE FROM rag_chunks")
    children = load_children(conn)
    titles = load_titles(conn)
    refs = source_refs(conn)
    summaries = {r["anime_id"]: r["text"] for r in conn.execute(
        "select anime_id, text from descriptions where kind='record_summary'")}

    rows = conn.execute(
        "select anime_id, title_canonical, title_english, type, year, synopsis, synopsis_source "
        "from anime where title_canonical is not null or title_english is not null").fetchall()

    n = 0
    per_kind: dict[str, int] = {}
    for row in rows:
        aid = row["anime_id"]
        title = row["title_canonical"] or row["title_english"]
        meta = dict(row)
        meta["summary"] = summaries.get(aid)
        anime_refs = refs.get(aid, [])
        chunks = build_chunks(title, meta, children, anime_refs, titles)
        seen: set[str] = set()
        idx = 0
        for kind, text, fields in chunks:
            text = text.strip()
            if text and not text.endswith((".", "!", "?", '"', "」", "』")):
                text += "."
            if len(text) < 30 or text in seen:
                continue
            seen.add(text)
            chunk_refs = [dict(r) for r in anime_refs]
            for r in chunk_refs:
                r["fields"] = fields
            if not chunk_refs:
                chunk_refs = [{"source": "derived", "fields": fields}]
            prose_source = (normalize_source(row["synopsis_source"])
                            if kind == "source_synopsis" else None)
            conn.execute(
                "INSERT INTO rag_chunks(anime_id, chunk_index, kind, text, source_refs, "
                "prose_source) VALUES(?,?,?,?,?,?)",
                (aid, idx, kind, text, json.dumps(chunk_refs, ensure_ascii=False),
                 prose_source))
            idx += 1
            n += 1
            per_kind[kind] = per_kind.get(kind, 0) + 1
    conn.commit()
    cp_set(conn, "rag_done", n)
    log(conn, "rag", f"chunks={n} kinds={per_kind}")
    print(json.dumps({"rag_chunks": n, "by_kind": per_kind}, indent=2))
    conn.close()
    return 0
