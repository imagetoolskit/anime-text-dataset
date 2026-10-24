"""Shared fact loading for the text-generation stages.

The QA, instruction and RAG builders all need the same child records. Loading
them once per stage into dictionaries is dramatically cheaper than issuing
eight queries per anime (35k anime x 8 queries).
"""

import json


def _uniq(values):
    """Order-preserving dedupe: two sources often name the same studio twice."""
    seen = set()
    out = []
    for value in values:
        key = value.lower() if isinstance(value, str) else value
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out


def load_children(conn) -> dict:
    genres: dict[int, list[str]] = {}
    themes: dict[int, list[str]] = {}
    studios: dict[int, list[str]] = {}
    alts: dict[int, list[dict]] = {}
    chars: dict[int, list[dict]] = {}
    staff: dict[int, list[dict]] = {}
    episodes: dict[int, list[dict]] = {}
    relations: dict[int, list[dict]] = {}
    franchise: dict[int, list[int]] = {}

    for r in conn.execute("select anime_id, genre from anime_genres order by anime_id, genre"):
        genres.setdefault(r[0], []).append(r[1])
    for r in conn.execute("select anime_id, theme from anime_themes order by anime_id, theme"):
        themes.setdefault(r[0], []).append(r[1])
    for r in conn.execute("select anime_id, studio_name from anime_studios "
                          "order by anime_id, is_main desc, studio_name"):
        studios.setdefault(r[0], []).append(r[1])
    for r in conn.execute("select anime_id, title, lang, kind from alt_titles "
                          "order by anime_id, kind"):
        alts.setdefault(r[0], []).append({"title": r[1], "lang": r[2], "kind": r[3]})
    for r in conn.execute("select anime_id, name, role, voice_actors from characters "
                          "order by anime_id, id"):
        vas = []
        try:
            vas = [v.get("name") for v in json.loads(r["voice_actors"] or "[]") if v.get("name")]
        except (TypeError, json.JSONDecodeError):
            vas = []
        chars.setdefault(r[0], []).append(
            {"name": r["name"], "role": r["role"], "va": vas[0] if vas else None})
    for r in conn.execute("select anime_id, name, roles from staff order by anime_id, id"):
        try:
            roles = json.loads(r["roles"] or "[]")
        except (TypeError, json.JSONDecodeError):
            roles = []
        staff.setdefault(r[0], []).append({"name": r["name"], "roles": _uniq(roles)})
    for r in conn.execute("select anime_id, number, title from episodes "
                          "where title is not null order by anime_id, number"):
        episodes.setdefault(r[0], []).append({"number": r[1], "title": r[2]})
    for r in conn.execute("select anime_id, other_anime_id, relation from relationships "
                          "order by anime_id"):
        relations.setdefault(r[0], []).append({"other": r[1], "relation": r[2]})
    for r in conn.execute("select franchise_id, anime_id from franchises order by franchise_id"):
        franchise.setdefault(r[0], []).append(r[1])
    # Franchises are keyed by franchise id in the table; the text stages need
    # anime_id -> sibling anime_ids, so invert the grouping here.
    siblings: dict[int, list[int]] = {}
    for members in franchise.values():
        for aid in members:
            siblings[aid] = members

    for mapping in (genres, themes, studios):
        for aid in list(mapping):
            mapping[aid] = _uniq(mapping[aid])
    for aid, items in relations.items():
        relations[aid] = list({(i["other"], i["relation"]): i for i in items}.values())
    for aid, items in alts.items():
        seen = set()
        kept = []
        for item in items:
            key = ((item.get("title") or "").lower(), item.get("kind"))
            if key not in seen:
                seen.add(key)
                kept.append(item)
        alts[aid] = kept

    return {"genres": genres, "themes": themes, "studios": studios, "alts": alts,
            "chars": chars, "staff": staff, "episodes": episodes, "relations": relations,
            "franchise": siblings}


def load_titles(conn) -> dict[int, str]:
    return {r[0]: (r[1] or r[2]) for r in conn.execute(
        "select anime_id, title_canonical, title_english from anime")}


def load_episode_counts(conn) -> dict[int, int]:
    return {r[0]: r[1] for r in conn.execute(
        "select anime_id, episodes from anime where episodes is not null")}


def load_years(conn) -> dict[int, int]:
    return {r[0]: r[1] for r in conn.execute(
        "select anime_id, year from anime where year is not null")}


def find_staff(staff: list[dict], wanted: tuple[str, ...],
               exclude: tuple[str, ...] = ("assistant", "episode", "adr", "dub")) -> list[str]:
    """Names credited with a role containing one of `wanted`.

    `exclude` filters out nearby credit types that share a word with the wanted
    role: "ADR Director" and "Episode Director" are not "Director".
    """
    out = []
    for member in staff:
        for role in member["roles"]:
            low = role.lower()
            if not any(w in low for w in wanted):
                continue
            if any(x in low for x in exclude):
                continue
            out.append(member["name"])
            break
    return out


DIRECTOR_EXCLUDE = ("assistant", "episode", "adr", "sound", "art", "animation", "unit",
                    "action", "3d", "photography", "dub")
MUSIC_EXCLUDE = ("producer", "theme", "insert", "arrangement", "lyrics", "performance",
                 "selection", "director")
WRITER_EXCLUDE = ("assistant", "episode", "adr", "dub")
