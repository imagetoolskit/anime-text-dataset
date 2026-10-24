"""Instruction-tuning records.

Every example is derivable from its own input. The previous version failed that
test: `metadata_extraction` asked the model to read a synopsis and produce the
title, year, type, status and genres, none of which appeared in the text, so the
correct answer was unlearnable.

Each builder below renders the source facts into the `input` field first, then
asks for a transformation of exactly those facts.
"""

import json
import random

from ..config import load
from ..db import connect, cp_set, log
from .descriptions import TYPE_LABEL, build_description
from .facts import (DIRECTOR_EXCLUDE, MUSIC_EXCLUDE, WRITER_EXCLUDE, find_staff,
                    load_children, load_titles, load_years)

PURPOSE = {
    "metadata_extraction": "Teach copying structured fields into JSON without inventing values.",
    "record_summarization": "Teach faithful prose summaries of a structured record.",
    "character_extraction": "Teach cast extraction with roles and voice actors.",
    "staff_credits": "Teach credit extraction grouped by role.",
    "episode_list": "Teach ordered episode-list extraction.",
    "relation_extraction": "Teach relationship extraction from prose.",
    "franchise_grouping": "Teach chronological ordering inside a franchise.",
    "title_normalization": "Teach canonical title selection and alias handling.",
    "entity_resolution": "Teach matching a described work to one candidate title.",
    "comparison": "Teach numeric comparison grounded in both records.",
    "json_repair": "Teach syntax repair without changing values.",
    "abstention": "Teach null output when a field is genuinely absent.",
}


def jdump(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def type_label(t: str | None) -> str:
    return TYPE_LABEL.get(t or "", (t or "anime work"))


def card(facts: dict, fields: list[tuple[str, object]]) -> str:
    lines = []
    for label, value in fields:
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def base_fields(facts: dict, children: dict) -> list[tuple[str, object]]:
    aid = facts["anime_id"]
    return [
        ("Title", facts["title"]),
        ("Japanese title", facts.get("title_japanese")),
        ("Format", type_label(facts.get("type")) if facts.get("type") else None),
        ("Status", facts.get("status")),
        ("Release year", facts.get("year")),
        ("First aired", facts.get("aired_from")),
        ("Episodes", facts.get("episodes")),
        ("Episode runtime (minutes)", facts.get("duration_min")),
        ("Source material", (facts.get("source_material") or "").replace("_", " ").title() or None),
        ("Genres", children["genres"].get(aid)),
        ("Themes", children["themes"].get(aid, [])[:8]),
        ("Studios", children["studios"].get(aid)),
        ("Mean score (out of 100)", facts.get("mean_score")),
    ]


def make_metadata(facts, children) -> dict | None:
    aid = facts["anime_id"]
    record = {
        "title": facts["title"],
        "type": type_label(facts.get("type")) if facts.get("type") else None,
        "year": facts.get("year"),
        "episodes": facts.get("episodes"),
        "status": facts.get("status"),
        "genres": children["genres"].get(aid, []),
    }
    record = {k: v for k, v in record.items() if v not in (None, [], "")}
    if len(record) < 3:
        return None
    text = card(facts, [
        ("Title", record.get("title")),
        ("Format", record.get("type")),
        ("Release year", record.get("year")),
        ("Episodes", record.get("episodes")),
        ("Status", record.get("status")),
        ("Genres", record.get("genres")),
    ])
    return {
        "itype": "metadata_extraction",
        "instruction": ("Extract the record below into a JSON object with the keys "
                        "title, type, year, episodes, status and genres. Copy values exactly "
                        "as written. Omit any key that is not present in the record."),
        "input": text,
        "output": jdump(record),
    }


def make_summary(facts, children) -> dict | None:
    aid = facts["anime_id"]
    studios = children["studios"].get(aid, [])
    directors = find_staff(children["staff"].get(aid, []), ("director",), DIRECTOR_EXCLUDE)
    cast = [c["name"] for c in children["chars"].get(aid, []) if c["role"] == "Main"][:4]
    fields = base_fields(facts, children) + [("Director", directors[:2]), ("Main cast", cast)]
    row = {
        "anime_id": aid,
        "title_canonical": facts["title"],
        "title_english": facts.get("title_english"),
        "type": facts.get("type"),
        "aired_from": facts.get("aired_from"),
        "year": facts.get("year"),
        "episodes": facts.get("episodes"),
        "source_material": facts.get("source_material"),
        "mean_score": facts.get("mean_score"),
    }
    summary = build_description(row, children["genres"].get(aid, []),
                                children["themes"].get(aid, []), studios,
                                directors, cast)
    if not summary:
        return None
    return {
        "itype": "record_summarization",
        "instruction": ("Write a factual three-to-five sentence summary of the record below. "
                        "Use only the listed fields and do not add plot details."),
        "input": card(facts, fields),
        "output": summary,
    }


def make_characters(facts, children) -> dict | None:
    chars = [c for c in children["chars"].get(facts["anime_id"], [])
             if c["role"] in ("Main", "Supporting")][:10]
    if not chars:
        return None
    lines = []
    for c in chars:
        line = f"- {c['name']} — {c['role']}"
        if c["va"]:
            line += f" — voiced by {c['va']}"
        lines.append(line)
    out = [{"name": c["name"], "role": c["role"], "voice_actor": c["va"]} for c in chars]
    return {
        "itype": "character_extraction",
        "instruction": ("Extract every character in the cast list with their role and voice "
                        "actor. Return a JSON array of objects with the keys name, role and "
                        "voice_actor. Use null when a voice actor is not listed."),
        "input": f"Cast of {facts['title']}:\n" + "\n".join(lines),
        "output": jdump(out),
    }


def make_staff(facts, children) -> dict | None:
    by_role: dict[str, list[str]] = {}
    for member in children["staff"].get(facts["anime_id"], []):
        for role in member["roles"][:2]:
            if role:
                by_role.setdefault(role, []).append(member["name"])
    if not by_role:
        return None
    roles = sorted(by_role)[:8]
    lines = [f"- {role}: {', '.join(dict.fromkeys(by_role[role]))}" for role in roles]
    out = {role: list(dict.fromkeys(by_role[role])) for role in roles}
    return {
        "itype": "staff_credits",
        "instruction": ("Extract the production credits below into a JSON object that maps "
                        "each role to the list of people credited with it. Keep role names "
                        "exactly as written."),
        "input": f"Credits for {facts['title']}:\n" + "\n".join(lines),
        "output": jdump(out),
    }


def make_episodes(facts, children) -> dict | None:
    eps = children["episodes"].get(facts["anime_id"], [])[:24]
    if len(eps) < 2:
        return None
    lines = [f"{e['number']}. {e['title']}" for e in eps]
    out = [{"number": e["number"], "title": e["title"]} for e in eps]
    return {
        "itype": "episode_list",
        "instruction": ("Parse the episode list into a JSON array of objects with the keys "
                        "number and title. Preserve the given order."),
        "input": f"Episodes of {facts['title']}:\n" + "\n".join(lines),
        "output": jdump(out),
    }


def make_relations(facts, children, titles) -> dict | None:
    rels = [r for r in children["relations"].get(facts["anime_id"], [])
            if r["other"] in titles][:6]
    if not rels:
        return None
    lines = [f"- {titles[r['other']]} is a {r['relation'].lower().replace('_', ' ')} of "
             f"{facts['title']}." for r in rels]
    out = [{"title": titles[r["other"]], "relation": r["relation"].lower()} for r in rels]
    return {
        "itype": "relation_extraction",
        "instruction": ("Extract the work relationships described below. Return a JSON array "
                        "of objects with the keys title and relation."),
        "input": f"Relationships for {facts['title']}:\n" + "\n".join(lines),
        "output": jdump(out),
    }


def make_franchise(facts, children, titles, years) -> dict | None:
    aid = facts["anime_id"]
    members = [m for m in children["franchise"].get(aid, []) if m in titles]
    if len(members) < 3:
        return None
    members = sorted(members, key=lambda m: (years.get(m) or 9999, m))[:10]
    lines = []
    for m in members:
        relation = "same franchise"
        for r in children["relations"].get(aid, []):
            if r["other"] == m:
                relation = r["relation"].lower().replace("_", " ")
                break
        year = years.get(m)
        lines.append(f"- {titles[m]}" + (f" ({year})" if year else "") + f" — {relation}")
    out = [{"title": titles[m], "year": years.get(m)} for m in members]
    return {
        "itype": "franchise_grouping",
        "instruction": ("Order the franchise entries below from earliest to latest release. "
                        "Return a JSON array of objects with the keys title and year."),
        "input": f"Franchise entries related to {facts['title']}:\n" + "\n".join(lines)
                 + "\nNote: the list above is not in release order.",
        "output": jdump(out),
    }


def make_titles(facts, children) -> dict | None:
    aid = facts["anime_id"]
    alts = children["alts"].get(aid, [])
    if not alts and not facts.get("title_japanese"):
        return None
    lines = [f"- Canonical: {facts['title']}"]
    if facts.get("title_english"):
        lines.append(f"- English: {facts['title_english']}")
    if facts.get("title_japanese"):
        lines.append(f"- Japanese: {facts['title_japanese']}")
    for a in alts[:8]:
        if a["title"] and a["title"] != facts["title"]:
            label = (a["kind"] or a["lang"] or "alias").title()
            lines.append(f"- {label}: {a['title']}")
    out = {
        "canonical": facts["title"],
        "english": facts.get("title_english"),
        "japanese": facts.get("title_japanese"),
        "aliases": sorted({a["title"] for a in alts if a["title"] and a["title"] != facts["title"]}),
    }
    return {
        "itype": "title_normalization",
        "instruction": ("Normalize the title record below. Return a JSON object with canonical, "
                        "english, japanese and aliases. `aliases` must be a de-duplicated list "
                        "that excludes the canonical title."),
        "input": "\n".join(lines),
        "output": jdump(out),
    }


def article(label: str) -> str:
    return "an" if label[:1].lower() in "aeiou" else "a"


def make_entity_resolution(facts, children, pool, rng) -> dict | None:
    if not facts.get("year") or not facts.get("type"):
        return None
    target_key = (facts["year"], facts["type"])
    distractors = [p for p in pool
                   if p[0] != facts["anime_id"] and (p[2], p[3]) != target_key][:3]
    if len(distractors) < 2:
        return None
    candidates = [(facts["anime_id"], facts["title"], facts["year"], facts["type"])]
    candidates += distractors
    rng.shuffle(candidates)
    lines = [f"- {c[1]} ({c[2]}, {type_label(c[3])})" for c in candidates]
    return {
        "itype": "entity_resolution",
        "instruction": ("Match the description to exactly one candidate and return a JSON "
                        "object with the key title."),
        "input": ("Description: " + article(type_label(facts["type"])) + " "
                  + type_label(facts["type"]).lower() + " released in "
                  + str(facts["year"]) + ".\nCandidates:\n" + "\n".join(lines)),
        "output": jdump({"title": facts["title"]}),
    }


def make_json_repair(facts, children) -> dict | None:
    aid = facts["anime_id"]
    correct = {
        "title": facts["title"],
        "type": type_label(facts.get("type")) if facts.get("type") else None,
        "year": facts.get("year"),
        "episodes": facts.get("episodes"),
    }
    correct = {k: v for k, v in correct.items() if v not in (None, "")}
    if len(correct) < 3:
        return None
    broken = "{"
    parts = []
    for k, v in correct.items():
        val = f"'{v}'" if isinstance(v, str) else v
        parts.append(f"{k}: {val}")
    broken += ", ".join(parts) + ",}"
    return {
        "itype": "json_repair",
        "instruction": ("Repair the malformed JSON below so that it parses. Do not change, add "
                        "or remove any values; return only the corrected JSON object."),
        "input": broken,
        "output": jdump(correct),
    }


def make_abstention(facts, children) -> dict | None:
    checks = [
        ("studio", children["studios"].get(facts["anime_id"]), "Which studio animated this work?"),
        ("episodes", facts.get("episodes"), "How many episodes does this work have?"),
    ]
    for key, value, question in checks:
        if value:
            continue
        text = card(facts, [
            ("Title", facts["title"]),
            ("Format", type_label(facts.get("type")) if facts.get("type") else None),
            ("Genres", children["genres"].get(facts["anime_id"])),
        ])
        return {
            "itype": "abstention",
            "instruction": ("Answer the question using only the record below. If the record does "
                            "not contain the answer, return a JSON object with the field set to "
                            "null instead of guessing."),
            "input": text + f"\nQuestion: {question}\nField: {key}",
            "output": jdump({key: None}),
        }
    return None


def make_comparison(a, b) -> dict | None:
    ea, eb = a.get("episodes"), b.get("episodes")
    if not ea or not eb or ea == eb:
        return None
    more, less = (a, b) if ea > eb else (b, a)
    return {
        "itype": "comparison",
        "instruction": ("Compare the two records and answer which work has more episodes. "
                        "Support the answer with both episode counts."),
        "input": (f"Record A\n{card(a, [('Title', a['title']), ('Episodes', ea)])}\n\n"
                  f"Record B\n{card(b, [('Title', b['title']), ('Episodes', eb)])}"),
        "output": (f"{more['title']} has {more['episodes']} episodes, while "
                   f"{less['title']} has {less['episodes']}."),
    }


def run() -> int:
    cfg = load()
    rng = random.Random(cfg["seed"] + 7)
    conn = connect()
    conn.execute("DELETE FROM instructions")
    children = load_children(conn)
    titles = load_titles(conn)
    years = load_years(conn)

    rows = conn.execute(
        "select anime_id, title_canonical, title_english, title_japanese, type, status, year, "
        "aired_from, episodes, duration_min, mean_score, source_material "
        "from anime where title_canonical is not null or title_english is not null").fetchall()
    facts_list = []
    for row in rows:
        f = dict(row)
        f["title"] = row["title_canonical"] or row["title_english"]
        facts_list.append(f)

    pool = [(f["anime_id"], f["title"], f["year"], f["type"])
            for f in facts_list if f.get("year") and f.get("type")]
    rng.shuffle(pool)

    n = 0
    per_type: dict[str, int] = {}

    def emit(facts, item):
        nonlocal n
        if not item:
            return
        conn.execute(
            "INSERT INTO instructions(anime_id,itype,instruction,input,output,synthetic,"
            "source_record_ids,purpose,validation) VALUES(?,?,?,?,?,?,?,?,?)",
            (facts["anime_id"], item["itype"], item["instruction"],
             item.get("input") or "", item["output"], 1,
             json.dumps({"anime_id": facts["anime_id"]}),
             PURPOSE.get(item["itype"], ""),
             "derivable_by_construction"))
        n += 1
        per_type[item["itype"]] = per_type.get(item["itype"], 0) + 1

    for facts in facts_list:
        emit(facts, make_metadata(facts, children))
        emit(facts, make_summary(facts, children))
        emit(facts, make_characters(facts, children))
        emit(facts, make_staff(facts, children))
        emit(facts, make_episodes(facts, children))
        emit(facts, make_relations(facts, children, titles))
        emit(facts, make_franchise(facts, children, titles, years))
        emit(facts, make_titles(facts, children))
        emit(facts, make_json_repair(facts, children))
        if rng.random() < 0.25:
            emit(facts, make_entity_resolution(facts, children, pool, rng))
        if rng.random() < 0.10:
            emit(facts, make_abstention(facts, children))

    # Comparisons: prefer franchise siblings (meaningful), then a same-year,
    # same-format peer. Both ensure the two titles are comparable rather than
    # randomly paired.
    by_id = {f["anime_id"]: f for f in facts_list}
    peers: dict[tuple[str, int], list[int]] = {}
    for f in facts_list:
        if f.get("type") and f.get("year"):
            peers.setdefault((f["type"], f["year"]), []).append(f["anime_id"])
    compared = 0
    for facts in facts_list:
        aid = facts["anime_id"]
        partners = [m for m in children["franchise"].get(aid, []) if m in by_id and m != aid]
        if not partners and facts.get("type") and facts.get("year"):
            same = [m for m in peers.get((facts["type"], facts["year"]), []) if m != aid]
            if len(same) >= 2 and rng.random() < 0.25:
                partners = same
        if not partners:
            continue
        partner = by_id[partners[rng.randrange(len(partners))]]
        before = n
        emit(facts, make_comparison(facts, partner))
        if n > before:
            compared += 1

    conn.commit()
    cp_set(conn, "instructions_done", n)
    log(conn, "instructions", f"items={n} types={len(per_type)}")
    print(json.dumps({"instructions": n, "by_type": per_type}, indent=2))
    conn.close()
    return 0
