"""Question-answer generation.

Design rules, enforced by construction:

* A pair is only emitted when every value in the answer is present in the
  database for that anime. Nothing is inferred or completed by guesswork.
* Each question type has several phrasings, chosen deterministically per anime,
  so the corpus does not read like one repeated template.
* Answers are short natural-language sentences with correct pluralization and
  serial commas.
* Abstention pairs are capped at roughly one in twenty pairs so honest
  "not recorded" answers teach calibration instead of dominating the corpus.
"""

import json
import random

from ..config import load
from ..db import connect, cp_set, log
from .attribution import normalize_source
from .facts import DIRECTOR_EXCLUDE, MUSIC_EXCLUDE, WRITER_EXCLUDE

TYPE_LABEL = {
    "TV": ("TV series", "anime series"),
    "MOVIE": ("anime film", "film"),
    "OVA": ("OVA", "original video animation"),
    "ONA": ("ONA", "original net animation"),
    "SPECIAL": ("TV special", "special"),
    "TV_SPECIAL": ("TV special", "special"),
    "SHORT": ("short", "short-form anime"),
    "TV_SHORT": ("short TV series", "short-form series"),
    "ONA_SHORT": ("short ONA", "short-form ONA"),
    "MUSIC": ("music video", "animated music video"),
    "PV": ("promotional video", "promo video"),
    "CM": ("commercial", "advertisement"),
}

SOURCE_LABEL = {
    "MANGA": "a manga",
    "LIGHT_NOVEL": "a light novel",
    "NOVEL": "a novel",
    "WEB_NOVEL": "a web novel",
    "WEB_MANGA": "a web manga",
    "VISUAL_NOVEL": "a visual novel",
    "VIDEO_GAME": "a video game",
    "CARD_GAME": "a card game",
    "GAME": "a game",
    "ORIGINAL": None,
    "ANIME": "an earlier anime",
    "MUSIC": "a music release",
    "BOOK": "a book",
    "PICTURE_BOOK": "a picture book",
    "RADIO": "a radio program",
    "LIVE_ACTION": "a live-action work",
    "MIXED_MEDIA": "a mixed-media project",
    "DOUJINSHI": "a doujinshi",
    "OTHER": "other source material",
}

RELATION_QUESTION = {
    "SEQUEL": "sequel",
    "PREQUEL": "prequel",
    "SIDE_STORY": "side story",
    "SPIN_OFF": "spin-off",
    "PARENT_STORY": "parent story",
    "FULL_STORY": "full story",
    "ALTERNATIVE_SETTING": "alternative setting",
    "ALTERNATIVE_VERSION": "alternative version",
    "SUMMARY": "summary",
    "ADAPTATION": "adaptation",
}

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def plural(n: int, singular: str, plural_form: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural_form or singular + 's')}"


def join_list(items: list[str], conj: str = "and") -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return f"{', '.join(items[:-1])}, {conj} {items[-1]}"


def fmt_date(value: str | None) -> str | None:
    if not value:
        return None
    parts = value.split("-")
    if len(parts) == 3:
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if 1 <= m <= 12 and 1 <= d <= 31:
                return f"{d} {MONTHS[m - 1]} {y}"
        except ValueError:
            return None
    if len(parts) >= 1 and parts[0].isdigit():
        return parts[0]
    return None


def fmt_score(value) -> str | None:
    if value is None:
        return None
    return f"{float(value):.1f}"


def pick(rng: random.Random, options: list[str]) -> str:
    return options[rng.randrange(len(options))]


def _load_children(conn) -> dict:
    from .facts import load_children
    return load_children(conn)


def _titles(conn) -> dict[int, str]:
    from .facts import load_titles
    return load_titles(conn)


def _main_cast(chars: list[dict], limit: int = 5) -> list[str]:
    return [c["name"] for c in chars if (c["role"] or "").lower() == "main"][:limit]


def _find_staff(staff: list[dict], wanted: tuple[str, ...],
                exclude: tuple[str, ...] = ("assistant", "episode", "adr", "dub")) -> list[str]:
    from .facts import find_staff
    return find_staff(staff, wanted, exclude)


def build_pairs(facts: dict, children: dict, titles: dict, rng: random.Random) -> list[dict]:
    aid = facts["anime_id"]
    title = facts["title"]
    out: list[dict] = []

    def add(qtype, question, answer, template, fields, prose_source=None):
        if not question or not answer:
            return
        clean_q = question.strip()
        clean_a = answer.strip()
        if len(clean_a) < 12 or clean_q.count("{") or clean_a.count("{"):
            return
        out.append({"qtype": qtype, "question": clean_q, "answer": clean_a,
                    "template": template, "fields": fields,
                    "prose_source": prose_source})

    type_label = TYPE_LABEL.get(facts["type"] or "", None)
    if type_label:
        label = pick(rng, list(type_label))
        add("type", pick(rng, [
            f"What type of work is {title}?",
            f"Is {title} a TV series, a film, or another format?",
            f"What format is {title}?"]),
            f"{title} is a {label}.", "type:v2", ["type"])

    if facts["aired_from"]:
        date = fmt_date(facts["aired_from"])
        if date:
            verb = "premiered" if (facts["type"] or "").startswith("TV") else "was released"
            add("air_date", pick(rng, [
                f"When did {title} first air?",
                f"When was {title} released?",
                f"What is the original release date of {title}?"]),
                f"{title} {verb} on {date}.", "air_date:v2", ["aired_from"])
    elif facts["year"]:
        add("air_date", f"When was {title} released?",
            f"{title} was released in {facts['year']}.", "air_date_year:v2", ["year"])

    if facts["episodes"] and facts["episodes"] > 0:
        n = facts["episodes"]
        add("episode_count", pick(rng, [
            f"How many episodes does {title} have?",
            f"What is the episode count for {title}?",
            f"How long is {title} in episodes?"]),
            (f"{title} consists of a single episode." if n == 1
             else f"{title} has {plural(n, 'episode')}."), "episode_count:v2", ["episodes"])

    if facts["duration_min"] and facts["duration_min"] > 0:
        d = facts["duration_min"]
        if (facts["type"] or "") == "MOVIE":
            add("runtime", f"How long is {title}?",
                f"{title} runs for {plural(d, 'minute')}.", "runtime:v2", ["duration_min"])
        else:
            add("runtime", f"How long is each episode of {title}?",
                f"Each episode of {title} runs about {plural(d, 'minute')}.",
                "episode_runtime:v2", ["duration_min"])

    studios = children["studios"].get(aid, [])
    if studios:
        add("studio", pick(rng, [
            f"Which studio animated {title}?",
            f"Who produced the animation for {title}?",
            f"What animation studio worked on {title}?"]),
            f"{title} was animated by {join_list(studios[:3])}.", "studio:v2", ["studios"])

    genres = children["genres"].get(aid, [])
    if genres:
        add("genres", pick(rng, [
            f"What genres does {title} belong to?",
            f"Which genres are associated with {title}?",
            f"How would you classify the genre of {title}?"]),
            f"{title} is associated with the {join_list(genres[:5])} genres.",
            "genres:v2", ["genres"])

    themes = children["themes"].get(aid, [])
    if themes:
        add("themes", pick(rng, [
            f"What themes does {title} explore?",
            f"Which thematic tags describe {title}?",
            f"What subjects does {title} deal with?"]),
            f"{title} explores themes such as {join_list(themes[:4])}.",
            "themes:v2", ["themes"])

    source = facts["source_material"]
    if source and source in SOURCE_LABEL:
        label = SOURCE_LABEL[source]
        if label is None:
            add("source", f"What is {title} based on?",
                f"{title} is an original work rather than an adaptation.",
                "source_original:v2", ["source_material"])
        else:
            add("source", pick(rng, [
                f"What is {title} based on?",
                f"Was {title} adapted from another work?",
                f"What source material does {title} adapt?"]),
                f"{title} is based on {label}.", "source:v2", ["source_material"])

    # Upstream synopsis. The answer is the source text, not a paraphrase, so the
    # pair carries `prose_source` and is excluded from the project's CC-BY grant.
    synopsis = (facts.get("synopsis") or "").strip()
    if len(synopsis) >= 80:
        answer = synopsis
        if len(answer) > 1200:
            cut = answer[:1200]
            for sep in (". ", "! ", "? "):
                pos = cut.rfind(sep)
                if pos > 600:
                    cut = cut[:pos + 1]
                    break
            answer = cut
        add("synopsis", pick(rng, [
            f"What is the premise of {title}?",
            f"Summarize the story of {title}.",
            f"What happens in {title}?"]),
            answer, "synopsis:v2", ["anime.synopsis"],
            prose_source=normalize_source(facts.get("synopsis_source")))

    if facts["mean_score"]:
        score = fmt_score(facts["mean_score"])
        add("score", pick(rng, [
            f"What score does {title} have?",
            f"How is {title} rated?",
            f"What is the mean audience score for {title}?"]),
            f"{title} has a mean score of {score} out of 100.", "score:v2", ["mean_score"])

    if facts["favourites"]:
        add("favourites", f"How many users have favourited {title}?",
            f"{title} has been favourited by {facts['favourites']:,} AniList users.",
            "favourites:v2", ["favourites"])

    if facts["title_english"] and facts["title_english"] != title:
        add("english_title", f"What is the English title of {title}?",
            f"The English title of {title} is {facts['title_english']}.",
            "english_title:v2", ["title_english"])
    if facts["title_japanese"]:
        add("japanese_title", f"What is the Japanese title of {title}?",
            f"The Japanese title of {title} is {facts['title_japanese']}.",
            "japanese_title:v2", ["title_japanese"])

    alts = [a["title"] for a in children["alts"].get(aid, []) if a["title"] != title][:4]
    if alts:
        add("alt_titles", pick(rng, [
            f"What other titles is {title} known by?",
            f"Does {title} have alternative titles?"]),
            f"{title} is also known as {join_list(alts)}.", "alt_titles:v2", ["alt_titles"])

    chars = children["chars"].get(aid, [])
    main = _main_cast(chars)
    if main:
        add("characters", pick(rng, [
            f"Who are the main characters of {title}?",
            f"Name the main cast of {title}.",
            f"Which characters lead the story in {title}?"]),
            f"The main characters of {title} are {join_list(main)}.",
            "characters:v2", ["characters"])

    with_va = [c for c in chars if c["va"]]
    if with_va:
        c = with_va[rng.randrange(len(with_va))]
        add("voice_actor", pick(rng, [
            f"Who voices {c['name']} in {title}?",
            f"Which voice actor plays {c['name']} in {title}?"]),
            f"{c['name']} is voiced by {c['va']} in {title}.",
            "voice_actor:v2", ["characters.voice_actors"])

    if len(chars) >= 1:
        c = chars[rng.randrange(len(chars))]
        if c["role"] in ("Main", "Supporting"):
            word = "a main character" if c["role"] == "Main" else "a supporting character"
            add("character_role", f"What role does {c['name']} play in {title}?",
                f"{c['name']} is {word} in {title}.", "character_role:v2", ["characters.role"])

    staff = children["staff"].get(aid, [])
    directors = _find_staff(staff, ("director",), DIRECTOR_EXCLUDE)
    if directors:
        add("director", pick(rng, [
            f"Who directed {title}?",
            f"Who is the director of {title}?"]),
            f"{title} was directed by {join_list(directors[:2])}.",
            "director:v2", ["staff.roles"])
    composers = _find_staff(staff, ("music", "composer"), MUSIC_EXCLUDE)
    if composers:
        add("composer", f"Who composed the music for {title}?",
            f"The music for {title} was composed by {join_list(composers[:2])}.",
            "composer:v2", ["staff.roles"])
    writers = _find_staff(staff, ("series composition", "script", "screenplay"), WRITER_EXCLUDE)
    if writers:
        add("writer", f"Who wrote the script for {title}?",
            f"The script for {title} was written by {join_list(writers[:2])}.",
            "writer:v2", ["staff.roles"])

    eps = children["episodes"].get(aid, [])
    if eps:
        e = eps[rng.randrange(len(eps))]
        add("episode_title", f"What is episode {e['number']} of {title} called?",
            f"Episode {e['number']} of {title} is titled \"{e['title']}\".",
            "episode_title:v2", ["episodes.title"])

    rels = children["relations"].get(aid, [])
    rels = [r for r in rels if r["other"] and r["other"] in titles
            and r["relation"] in RELATION_QUESTION]
    seen_rel: set[tuple[int, str]] = set()
    for r in rels:
        key = (r["other"], r["relation"])
        if key in seen_rel:
            continue
        seen_rel.add(key)
        word = RELATION_QUESTION[r["relation"]]
        other_title = titles[r["other"]]
        add("relationship", f"What is the {word} of {title}?",
            f"The {word} of {title} is {other_title}.",
            f"relationship_{word.replace(' ', '_')}:v2", ["relationships"])
        break

    if rels:
        r = rels[rng.randrange(len(rels))]
        other_title = titles[r["other"]]
        word = RELATION_QUESTION[r["relation"]]
        add("relationship_reverse", f"How is {other_title} related to {title}?",
            f"{other_title} is the {word} of {title}.", "relationship_reverse:v2",
            ["relationships"])

    sibs = [titles[x] for x in children["franchise"].get(aid, [])
            if x != aid and x in titles][:3]
    if sibs:
        add("franchise", pick(rng, [
            f"Which other anime share a franchise with {title}?",
            f"What other series belong to the same franchise as {title}?"]),
            f"{title} shares a franchise with {join_list(sibs)}.",
            "franchise:v2", ["franchises"])

    # Multi-hop: resolve a relation, then read a field from the related work.
    if rels:
        r = rels[rng.randrange(len(rels))]
        other_id = r["other"]
        other_title = titles[other_id]
        word = RELATION_QUESTION[r["relation"]]
        other_studios = children["studios"].get(other_id, [])
        other_eps = (conn_rows_cache.get(other_id) or [None])[0]
        if other_studios:
            add("multi_hop_studio",
                f"Which studio animated the {word} of {title}, {other_title}?",
                f"The {word} of {title}, {other_title}, was animated by "
                f"{join_list(other_studios[:2])}.",
                "multi_hop_studio:v2", ["relationships", "studios"])
        if other_eps:
            add("multi_hop_episodes",
                f"How many episodes does the {word} of {title} have?",
                f"The {word} of {title}, {other_title}, has "
                f"{plural(other_eps, 'episode')}.",
                "multi_hop_episodes:v2", ["relationships", "episodes"])

    return out


conn_rows_cache: dict[int, list[int]] = {}


def build_abstentions(facts, has_studio: bool, rng) -> list[dict]:
    """At most one honest 'not recorded' pair, only for sparse records."""
    title = facts["title"]
    missing = []
    if not facts["episodes"]:
        missing.append(("unknown_episodes", f"How many episodes does {title} have?",
                        f"No episode count is recorded for {title} in this dataset.",
                        ["episodes"]))
    if not has_studio:
        missing.append(("unknown_studio", f"Which studio animated {title}?",
                        f"No animation studio is recorded for {title} in this dataset.",
                        ["studios"]))
    if not facts["mean_score"]:
        missing.append(("unknown_score", f"How is {title} rated?",
                        f"No audience score is recorded for {title} in this dataset.",
                        ["mean_score"]))
    if not missing:
        return []
    qtype, q, a, fields = missing[rng.randrange(len(missing))]
    return [{"qtype": qtype, "question": q, "answer": a,
             "template": f"{qtype}:v2", "fields": fields}]


def run() -> int:
    cfg = load()
    rng = random.Random(cfg["seed"])
    conn = connect()
    from .normalize import ensure_column
    ensure_column(conn, "qa_pairs", "prose_source", "TEXT")
    conn.execute("DELETE FROM qa_pairs")
    children = _load_children(conn)
    titles = _titles(conn)

    global conn_rows_cache
    conn_rows_cache = {aid: [n] for aid, n, _t, in conn.execute(
        "select anime_id, episodes, duration_min from anime where episodes is not null")}

    rows = conn.execute(
        "select anime_id, title_canonical, title_english, title_japanese, type, status, year, "
        "aired_from, aired_to, episodes, duration_min, mean_score, favourites, source_material, "
        "synopsis, synopsis_source "
        "from anime "
        "where title_canonical is not null or title_english is not null").fetchall()

    qa_cfg = cfg.get("qa_pairs_per_anime", {})
    per_anime_min = int(qa_cfg.get("min", 6))
    per_anime_max = int(qa_cfg.get("max", 14))
    n = 0
    for row in rows:
        aid = row["anime_id"]
        facts = dict(row)
        facts["title"] = row["title_canonical"] or row["title_english"]
        pairs = build_pairs(facts, children, titles, rng)
        pairs = [p for p in pairs if p["answer"]]
        seen_q: set[str] = set()
        unique = []
        for p in pairs:
            if p["question"] in seen_q:
                continue
            seen_q.add(p["question"])
            unique.append(p)
        if unique and rng.random() < 0.05:
            unique.extend(build_abstentions(
                facts, bool(children["studios"].get(aid)), rng))
        if not unique:
            continue
        rng.shuffle(unique)
        lo = min(per_anime_min, len(unique))
        hi = min(per_anime_max, len(unique))
        keep = rng.randint(lo, hi)
        selected = unique[:keep]
        # Sampling must not silently drop the one synopsis pair: it is the only
        # record of the upstream text and it carries the attribution field.
        synopsis_pair = next((p for p in unique if p["qtype"] == "synopsis"), None)
        if synopsis_pair and synopsis_pair not in selected:
            selected.append(synopsis_pair)
        for p in selected:
            conn.execute(
                "INSERT INTO qa_pairs(anime_id,qtype,question,answer,template,grounded_fields,"
                "prose_source) VALUES(?,?,?,?,?,?,?)",
                (aid, p["qtype"], p["question"], p["answer"],
                 p["template"], json.dumps(p["fields"]), p.get("prose_source")))
            n += 1
    conn.commit()
    cp_set(conn, "qa_done", n)
    log(conn, "qa", f"items={n} across {len(rows)} anime")
    print(f"qa_pairs={n}")
    conn.close()
    return 0
