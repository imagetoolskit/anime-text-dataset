import json

from ..db import connect, cp_get, cp_set, log


def _sources_for_anime(conn) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for row in conn.execute("select anime_id, source, remote_id from anime_source"):
        out.setdefault(row["anime_id"], {})[row["source"]] = row["remote_id"]
    return out


def extract_from_anilist_full(conn) -> int:
    rows = 0
    src_map = {r["remote_id"]: r["anime_id"]
               for r in conn.execute("select anime_id, remote_id from anime_source where source='anilist'")}
    cur = conn.execute("select remote_id, payload from raw_payload "
                       "where source='anilist' and remote_kind='media_full'")
    for row in cur:
        aid = src_map.get(row["remote_id"])
        if aid is None:
            continue
        p = json.loads(row["payload"])

        conn.execute("INSERT OR REPLACE INTO anime(anime_id) VALUES(?) ON CONFLICT(anime_id) DO NOTHING", (aid,))
        conn.execute(
            "UPDATE anime SET type=coalesce(type,?), status=coalesce(status,?), episodes=coalesce(episodes,?), "
            "duration_min=coalesce(duration_min,?), aired_from=coalesce(aired_from,?), aired_to=coalesce(aired_to,?), "
            "season=coalesce(season,?), year=coalesce(year,?), title_canonical=coalesce(title_canonical,?), "
            "title_english=coalesce(title_english,?), title_japanese=coalesce(title_japanese,?), "
            "synopsis=coalesce(synopsis,?), mean_score=coalesce(mean_score,?), popularity=coalesce(popularity,?), "
            "favourites=coalesce(favourites,?), source_material=coalesce(source_material,?), "
            "age_rating=coalesce(age_rating,?) WHERE anime_id=?",
            (
                {"TV": "tv", "MOVIE": "movie", "OVA": "ova", "ONA": "ona",
                 "SPECIAL": "special", "MUSIC": "short", "TV_SHORT": "short"}.get(p.get("format"), p.get("format")),
                p.get("status"), p.get("episodes"), p.get("duration"),
                _date(p.get("startDate")), _date(p.get("endDate")),
                p.get("season"), p.get("seasonYear"),
                (p.get("title") or {}).get("romaji"),
                (p.get("title") or {}).get("english"),
                (p.get("title") or {}).get("native"),
                p.get("description"), p.get("averageScore"), p.get("popularity"), p.get("favourites"),
                p.get("source"), p.get("ageRating"), aid,
            ),
        )
        title = (p.get("title") or {})
        for lang, kind in (("romaji", "romaji"), ("english", "english"), ("native", "native")):
            t = title.get(lang)
            if t:
                conn.execute("INSERT OR IGNORE INTO alt_titles(anime_id,source,lang,kind,title) VALUES(?,?,?,?,?)",
                             (aid, "anilist", lang, kind, t))
        for t in p.get("synonyms") or []:
            conn.execute("INSERT OR IGNORE INTO alt_titles(anime_id,source,lang,kind,title) VALUES(?,?,?,?,?)",
                         (aid, "anilist", None, "synonym", t))
        for g in p.get("genres") or []:
            conn.execute("INSERT OR IGNORE INTO anime_genres(anime_id,genre) VALUES(?,?)", (aid, g))
            conn.execute("INSERT OR IGNORE INTO genres(genre) VALUES(?)", (g,))
        for t in p.get("tags") or []:
            name = t.get("name")
            if name:
                conn.execute("INSERT OR IGNORE INTO anime_themes(anime_id,theme) VALUES(?,?)", (aid, name))
                conn.execute("INSERT OR IGNORE INTO themes(theme,description) VALUES(?,?)",
                             (name, t.get("description")))
        for edge in (p.get("studios") or {}).get("edges") or []:
            st = edge.get("node") or {}
            name = st.get("name")
            if name:
                conn.execute(
                    "INSERT OR IGNORE INTO anime_studios(anime_id,source,studio_name,source_studio_id,is_main) "
                    "VALUES(?,?,?,?,?)", (aid, "anilist", name, str(st.get("id")), 1 if edge.get("isMain") else 0))
                conn.execute("INSERT OR IGNORE INTO studios(studio_name,source_studio_id) VALUES(?,?)",
                             (name, str(st.get("id"))))
        for edge in (p.get("characters") or {}).get("edges") or []:
            node = edge.get("node") or {}
            if not node.get("id"):
                continue
            vas = [v.get("name", {}).get("native") or v.get("name", {}).get("full")
                   for v in edge.get("voiceActors") or []]
            conn.execute(
                "INSERT OR IGNORE INTO characters(anime_id,source,remote_id,name,name_native,role,description,voice_actors) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (aid, "anilist", str(node["id"]),
                 (node.get("name") or {}).get("romaji")
                 or (node.get("name") or {}).get("english")
                 or (node.get("name") or {}).get("full")
                 or (node.get("name") or {}).get("native"),
                 (node.get("name") or {}).get("native"),
                 edge.get("role"), node.get("description"),
                 json.dumps([v for v in vas if v], ensure_ascii=False)),
            )
        for edge in (p.get("staff") or {}).get("edges") or []:
            node = edge.get("node") or {}
            if not node.get("id"):
                continue
            conn.execute(
                "INSERT OR IGNORE INTO staff(anime_id,source,remote_id,name,name_native,roles) VALUES(?,?,?,?,?,?)",
                (aid, "anilist", str(node["id"]),
                 (node.get("name") or {}).get("full") or (node.get("name") or {}).get("native"),
                 (node.get("name") or {}).get("native"),
                 json.dumps([edge.get("role")] if edge.get("role") else [])),
            )
        conn.execute("INSERT OR REPLACE INTO provenance(entity,entity_id,source,url,retrieved_at,license_note,confidence) "
                     "VALUES(?,?,?,?,?,?,?)",
                     ("anime", str(aid), "anilist",
                      f"https://anilist.co/anime/{row['remote_id']}", _now(), _AL, 1.0))
        rows += 1
    conn.commit()
    return rows


def extract_from_shikimori(conn) -> int:
    rows = 0
    src_map = {r["remote_id"]: r["anime_id"]
               for r in conn.execute("select anime_id, remote_id from anime_source where source='shikimori'")}
    cur = conn.execute("select remote_id, payload from raw_payload where source='shikimori' and remote_kind='detail'")
    for row in cur:
        aid = src_map.get(row["remote_id"])
        if aid is None:
            continue
        p = json.loads(row["payload"])
        conn.execute("INSERT OR IGNORE INTO anime(anime_id) VALUES(?)", (aid,))
        conn.execute(
            "UPDATE anime SET type=coalesce(type,?), status=coalesce(status,?), episodes=coalesce(episodes,?), "
            "duration_min=coalesce(duration_min,?), aired_from=coalesce(aired_from,?), aired_to=coalesce(aired_to,?), "
            "year=coalesce(year,?), title_canonical=coalesce(title_canonical,?), "
            "title_japanese=coalesce(title_japanese,?), synopsis=coalesce(synopsis,?), "
            "mean_score=coalesce(mean_score,?), age_rating=coalesce(age_rating,?) WHERE anime_id=?",
            (
                {"tv": "tv", "movie": "movie", "ova": "ova", "ona": "ona",
                 "special": "special", "music": "short", "web": "web"}.get(p.get("kind"), p.get("kind")),
                p.get("status"), p.get("episodes"), p.get("duration"),
                p.get("aired_on"), p.get("released_on"),
                (p.get("aired_on") or "")[:4] or None,
                p.get("name"), " ".join(x for x in (p.get("japanese") or []) if x).strip() or None,
                " ".join(x for x in (p.get("description") or []) if x).strip() or None,
                p.get("score"), (p.get("rating") or [None])[0], aid,
            ),
        )
        for t in (p.get("english") or []):
            conn.execute("INSERT OR IGNORE INTO alt_titles(anime_id,source,lang,kind,title) VALUES(?,?,?,?,?)",
                         (aid, "shikimori", "english", "english", t))
        for t in (p.get("synonyms") or []):
            conn.execute("INSERT OR IGNORE INTO alt_titles(anime_id,source,lang,kind,title) VALUES(?,?,?,?,?)",
                         (aid, "shikimori", None, "synonym", t))
        if p.get("russian"):
            conn.execute("INSERT OR IGNORE INTO alt_titles(anime_id,source,lang,kind,title) VALUES(?,?,?,?,?)",
                         (aid, "shikimori", "ru", "russian", p["russian"]))
        for g in p.get("genres") or []:
            gname = g.get("name")
            if gname:
                if g.get("kind") == "theme":
                    conn.execute("INSERT OR IGNORE INTO anime_themes(anime_id,theme) VALUES(?,?)", (aid, gname))
                else:
                    conn.execute("INSERT OR IGNORE INTO anime_genres(anime_id,genre) VALUES(?,?)", (aid, gname))
                conn.execute("INSERT OR IGNORE INTO genres(genre) VALUES(?)", (gname,))
        for st in p.get("studios") or []:
            name = st.get("name")
            if name:
                conn.execute("INSERT OR IGNORE INTO anime_studios(anime_id,source,studio_name,source_studio_id,is_main) "
                             "VALUES(?,?,?,?,?)", (aid, "shikimori", name, str(st.get("id")), 0))
                conn.execute("INSERT OR IGNORE INTO studios(studio_name,source_studio_id,url) VALUES(?,?,?)",
                             (name, str(st.get("id")), f"https://shikimori.one/studios/{st.get('id')}"))
        rows += 1
    conn.commit()
    return rows


def extract_roles(conn) -> int:
    rows = 0
    src_map = {r["remote_id"]: r["anime_id"]
               for r in conn.execute("select anime_id, remote_id from anime_source where source='shikimori'")}
    todo = [r[0] for r in conn.execute(
        "select distinct s.remote_id from anime_source s where s.source='shikimori' and not exists ("
        " select 1 from raw_payload p where p.source='shikimori' and p.remote_kind='roles' and p.remote_id=s.remote_id)")]
    log(conn, "entities", f"shikimori roles pending: {len(todo)} (fetch in enrich phase)")
    return rows


def extract_roles_from_payloads(conn) -> int:
    rows = 0
    src_map = {r["remote_id"]: r["anime_id"]
               for r in conn.execute("select anime_id, remote_id from anime_source where source='shikimori'")}
    cur = conn.execute("select remote_id, payload from raw_payload where source='shikimori' and remote_kind='roles'")
    for row in cur:
        aid = src_map.get(row["remote_id"])
        if aid is None:
            continue
        for item in json.loads(row["payload"]):
            ch = item.get("character")
            person = item.get("person")
            roles = json.dumps(item.get("roles") or [], ensure_ascii=False)
            if ch and ch.get("id"):
                conn.execute(
                    "INSERT OR IGNORE INTO characters(anime_id,source,remote_id,name,name_native,role,voice_actors) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (aid, "shikimori", str(ch["id"]), ch.get("name"), ch.get("russian"),
                     roles, None))
                rows += 1
            if person and person.get("id"):
                conn.execute(
                    "INSERT OR IGNORE INTO staff(anime_id,source,remote_id,name,name_native,roles) VALUES(?,?,?,?,?,?)",
                    (aid, "shikimori", str(person["id"]), person.get("name"), person.get("russian"), roles))
                rows += 1
    conn.commit()
    return rows


def extract_episodes(conn) -> int:
    rows = 0
    cur = conn.execute("select remote_id, payload from raw_payload "
                       "where source='kitsu' and remote_kind='episodes'")
    kitsu_map = {r["remote_id"]: r["anime_id"]
                 for r in conn.execute("select remote_id, anime_id from anime_source where source='kitsu'")}
    for row in cur:
        ep = json.loads(row["payload"])
        rel = (ep.get("relationships") or {}).get("media", {}).get("data") or {}
        media_id = ep.get("_media_id") or rel.get("id")
        if rel.get("type") not in (None, "anime"):
            continue
        aid = kitsu_map.get(str(media_id))
        if aid is None:
            continue
        a = ep.get("attributes") or {}
        conn.execute(
            "INSERT OR IGNORE INTO episodes(anime_id,source,remote_id,number,title,synopsis,aired,length_min) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (aid, "kitsu", str(ep.get("id")), a.get("number"), a.get("canonicalTitle"),
             (a.get("synopsis") or "")[:2000] or None, a.get("airdate"), a.get("length")))
        rows += 1
    conn.commit()
    return rows


def _date(d: dict | None) -> str | None:
    if not d or not d.get("year"):
        return None
    month = d.get("month") or 1
    day = d.get("day") or 1
    return f"{int(d['year']):04d}-{int(month):02d}-{int(day):02d}"


def _now() -> str:
    from ..db import now
    return now()


_AL = "AniList public GraphQL API; retrieved via api docs.anilist.co"


def extract_from_kitsu(conn) -> int:
    rows = 0
    src_map = {r["remote_id"]: r["anime_id"]
               for r in conn.execute("select anime_id, remote_id from anime_source where source='kitsu'")}
    cur = conn.execute("select remote_id, payload from raw_payload where source='kitsu' and remote_kind='anime'")
    for row in cur:
        aid = src_map.get(row["remote_id"])
        if aid is None:
            continue
        p = json.loads(row["payload"])
        a = p.get("attributes") or {}
        titles = a.get("titles") or {}
        start = (a.get("startDate") or "")[:10] or None
        end = (a.get("endDate") or "")[:10] or None
        conn.execute("INSERT OR IGNORE INTO anime(anime_id) VALUES(?)", (aid,))
        conn.execute(
            "UPDATE anime SET type=coalesce(type,?), status=coalesce(status,?), "
            "episodes=coalesce(episodes,?), aired_from=coalesce(aired_from,?), "
            "aired_to=coalesce(aired_to,?), year=coalesce(year,?), "
            "title_canonical=coalesce(title_canonical,?), title_english=coalesce(title_english,?), "
            "title_japanese=coalesce(title_japanese,?), synopsis=coalesce(synopsis,?), "
            "synopsis_source=coalesce(synopsis_source,?), mean_score=coalesce(mean_score,?), "
            "popularity=coalesce(popularity,?), age_rating=coalesce(age_rating,?) WHERE anime_id=?",
            (
                {"TV": "tv", "movie": "movie", "OVA": "ova", "ONA": "ona",
                 "special": "special", "music": "short", "short": "short",
                 "TV_SHORT": "short", "ONA_SHORT": "short"}.get(a.get("subtype"), a.get("subtype")),
                {"current": "currently airing", "finished": "finished", "upcoming": "not yet aired"}.get(
                    a.get("status"), a.get("status")),
                a.get("episodeCount"), start, end,
                (start or "")[:4] or None,
                titles.get("en") or a.get("canonicalTitle"), titles.get("en"),
                titles.get("ja_jp") or titles.get("ja"),
                (a.get("synopsis") or "")[:4000] or None or None,
                "kitsu synopsis", a.get("averageRating"),
                a.get("popularityRank"), a.get("ageRating"),
                aid,
            ),
        )
        for lang_key in ("en", "ja_jp", "ja", "en_us", "en_ca", "en_gb", "en_jp"):
            t = titles.get(lang_key)
            if t and t != titles.get("en"):
                conn.execute("INSERT OR IGNORE INTO alt_titles(anime_id,source,lang,kind,title) "
                             "VALUES(?,?,?,?,?)", (aid, "kitsu", lang_key, "translation", t))
        if a.get("abbreviatedTitles"):
            for t in a["abbreviatedTitles"]:
                if t:
                    conn.execute("INSERT OR IGNORE INTO alt_titles(anime_id,source,lang,kind,title) "
                                 "VALUES(?,?,?,?,?)", (aid, "kitsu", None, "abbreviation", t))
        rows += 1
    conn.commit()
    return rows


def run() -> int:
    conn = connect()
    n1 = extract_from_anilist_full(conn)
    n2 = extract_from_shikimori(conn)
    n3 = extract_roles_from_payloads(conn)
    n4 = extract_episodes(conn)
    n5 = extract_from_kitsu(conn)
    cp_set(conn, "entities_done", True)
    log(conn, "entities", f"anilist_full={n1} shikimori={n2} roles={n3} episodes={n4} kitsu={n5}")
    print(f"anilist_full={n1} shikimori={n2} shikimori_roles={n3} episodes={n4} kitsu={n5}")
    conn.close()
    return 0
