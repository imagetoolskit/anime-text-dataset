import json
import re
import unicodedata

from ..db import connect, cp_get, cp_set, log, now

PUNCT_RE = re.compile(r"[\W_]", re.UNICODE)
WS_RE = re.compile(r"\s+")
LEADING_ARTICLE_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)
TAIL_SUFFIX_RE = re.compile(
    r"\s*[:\-]\s*(tv|movie|ova|ona|special|web|music|film|season\s*\d+)$", re.IGNORECASE
)

TYPE_MAP = {
    "TV": "tv", "MOVIE": "movie", "OVA": "ova", "ONA": "ona",
    "SPECIAL": "special", "MUSIC": "short", "TV_SHORT": "short",
    "NOVEL": "tv", "MANGA": None, "ONE_SHOT": None,
    "tv": "tv", "movie": "movie", "ova": "ova", "ona": "ona",
    "special": "special", "music": "short", "short": "short",
    "dorama": None, "web": "web",
}


def norm_title(title: str | None) -> str | None:
    if not title:
        return None
    t = unicodedata.normalize("NFKC", title).casefold()
    t = t.replace("&", " and ")
    t = PUNCT_RE.sub("", t)
    t = LEADING_ARTICLE_RE.sub("", t)
    t = TAIL_SUFFIX_RE.sub("", t)
    t = "".join(t.split())
    return t or None


def year_of(payload: dict) -> int | None:
    for key in ("startDate", "aired_on", "start_date", "airdate"):
        v = payload.get(key)
        if isinstance(v, dict):
            y = v.get("year")
            return int(y) if y else None
        if isinstance(v, str) and len(v) >= 4 and v[:4].isdigit():
            return int(v[:4])
    v = payload.get("seasonYear") or payload.get("season_year") or payload.get("year")
    if v:
        try:
            return int(v)
        except (TypeError, ValueError):
            pass
    return None


def map_type(raw: str | None) -> str | None:
    if not raw:
        return None
    return TYPE_MAP.get(raw, TYPE_MAP.get(raw.lower()))


def build_records(conn):
    anilist, kitsu, shikimori, wikidata = [], [], [], []
    cur = conn.execute(
        "select remote_id, payload from raw_payload where source='anilist' and remote_kind='media_light'"
    )
    for row in cur:
        p = json.loads(row["payload"])
        titles = [p.get("title", {}).get(k) for k in ("romaji", "english", "native")]
        anilist.append({
            "source": "anilist", "remote_id": row["remote_id"],
            "titles": [t for t in titles if t],
            "mal_id": str(p["idMal"]) if p.get("idMal") else None,
            "year": year_of(p), "type": map_type(p.get("format")),
            "pop": p.get("popularity"), "score": p.get("averageScore"),
        })
    cur = conn.execute("select remote_id, payload from raw_payload where source='kitsu' and remote_kind='anime'")
    for row in cur:
        p = json.loads(row["payload"])["attributes"]
        tset = p.get("titles") or {}
        titles = [p.get("canonicalTitle")] + list(tset.values())
        kitsu.append({
            "source": "kitsu", "remote_id": row["remote_id"],
            "titles": [t for t in titles if t],
            "mal_id": None, "year": year_of(p),
            "type": map_type(p.get("subtype")),
            "pop": p.get("popularityRank"), "score": None,
        })
    cur = conn.execute("select remote_id, payload from raw_payload where source='shikimori' and remote_kind='anime'")
    for row in cur:
        p = json.loads(row["payload"])
        titles = [p.get("name"), p.get("russian")] + (p.get("english") or []) + (p.get("synonyms") or [])
        shikimori.append({
            "source": "shikimori", "remote_id": row["remote_id"],
            "titles": [t for t in titles if t],
            "mal_id": str(p["myanimelist_id"]) if p.get("myanimelist_id") else None,
            "year": year_of(p), "type": map_type(p.get("kind")),
            "pop": None, "score": p.get("score"),
        })
    cur = conn.execute("select remote_id, payload from raw_payload where source='wikidata' and remote_kind='item'")
    for row in cur:
        p = json.loads(row["payload"])
        mal = (p.get("malId") or {}).get("value")
        en = (p.get("enLabel") or {}).get("value")
        if not en:
            en = (p.get("itemLabel") or {}).get("value") or p.get("itemLabel")
        wikidata.append({
            "source": "wikidata", "remote_id": row["remote_id"],
            "titles": [en],
            "mal_id": str(mal) if mal else None,
            "year": year_of(p), "type": "tv",
            "pop": None, "score": None,
        })
    return anilist, kitsu, shikimori, wikidata


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def run() -> int:
    conn = connect()
    if cp_get(conn, "dedup_done"):
        log(conn, "dedup", "already done, skipping (delete checkpoint 'dedup_done' to rerun)")
        conn.close()
        return 0

    anilist, kitsu, shikimori, wikidata = build_records(conn)
    log(conn, "dedup",
        f"records: anilist={len(anilist)} kitsu={len(kitsu)} shikimori={len(shikimori)} wikidata={len(wikidata)}")

    uf = UnionFind()
    key_of = {}
    all_recs = anilist + kitsu + shikimori + wikidata
    for i, rec in enumerate(all_recs):
        key_of[("src", rec["source"], rec["remote_id"])] = i
        uf.find(i)

    mal_index: dict[str, int] = {}
    for i, rec in enumerate(all_recs):
        if rec["mal_id"]:
            if rec["mal_id"] in mal_index:
                uf.union(mal_index[rec["mal_id"]], i)
            else:
                mal_index[rec["mal_id"]] = i

    title_year: dict[tuple[str, int | None], int] = {}
    link_methods = {}
    for i, rec in enumerate(all_recs):
        for t in rec["titles"]:
            nt = norm_title(t)
            if not nt:
                continue
            k = (nt, rec["year"])
            if k in title_year:
                uf.union(title_year[k], i)
            else:
                title_year[k] = i
            k2 = (nt, None)
            if k2 not in title_year:
                title_year[k2] = i

    groups: dict[int, list[int]] = {}
    for i in range(len(all_recs)):
        groups.setdefault(uf.find(i), []).append(i)

    by_source = {"anilist": {}, "kitsu": {}, "shikimori": {}, "wikidata": {}}
    for rec_list in (anilist, kitsu, shikimori, wikidata):
        for rec in rec_list:
            by_source[rec["source"]][rec["remote_id"]] = rec

    SRC_PRIORITY = ["anilist", "kitsu", "shikimori", "wikidata"]

    anime_id = 0
    conn.execute("DELETE FROM anime")
    conn.execute("DELETE FROM anime_source")
    conn.execute("DELETE FROM dedup_log")
    stats = {"clusters": 0, "multi_source": 0, "method_counts": {},
             "tiers": {}, "merged_external": 0}

    def method_for(members):
        sources = {all_recs[i]["source"] for i in members}
        mals = [all_recs[i]["mal_id"] for i in members if all_recs[i]["mal_id"]]
        if len(sources) > 1 and len(set(mals)) == 1 and mals:
            m = "mal_id"
        elif len(sources) > 1:
            m = "title_year"
        elif "anilist" in sources:
            m = "anilist_primary"
        elif "kitsu" in sources:
            m = "kitsu_primary"
        elif "shikimori" in sources:
            m = "shikimori_primary"
        else:
            m = "wikidata_primary"
        stats["method_counts"][m] = stats["method_counts"].get(m, 0) + 1
        return m

    CONF = {"mal_id": 1.0, "title_year": 0.8, "anilist_primary": 1.0,
            "kitsu_primary": 1.0, "shikimori_primary": 1.0, "wikidata_primary": 0.7}

    for members in groups.values():
        anime_id += 1
        stats["clusters"] += 1
        sources = {all_recs[i]["source"] for i in members}
        if len(sources) > 1:
            stats["multi_source"] += 1
        method = method_for(members)
        members_sorted = sorted(members, key=lambda i: SRC_PRIORITY.index(all_recs[i]["source"]))
        canon = all_recs[members_sorted[0]]

        title = (canon["titles"][0] if canon["titles"] else None)
        if title is None:
            for i in members_sorted:
                if all_recs[i]["titles"]:
                    title = all_recs[i]["titles"][0]
                    break
        tier = "A" if (len(sources) >= 2 and method in ("mal_id", "title_year")) else (
            "B" if len(sources) >= 2 else ("B" if canon["source"] != "wikidata" else "C"))
        if canon["source"] == "wikidata" and len(sources) == 1:
            tier = "C"
        conf = max(CONF[method], 0.7)
        pop = None
        score = None
        for rec in [all_recs[i] for i in members_sorted]:
            if pop is None and rec.get("pop"):
                pop = rec["pop"]
            if score is None and rec.get("score"):
                score = rec["score"]
        stats["tiers"][tier] = stats["tiers"].get(tier, 0) + 1
        conn.execute(
            "INSERT OR REPLACE INTO anime(anime_id,title_canonical,type,year,popularity,mean_score,quality_tier,confidence) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (anime_id, title, canon["type"], canon["year"], pop, score,
             tier, conf if tier in ("A", "B") else "low"))
        conn.execute(
            "INSERT INTO dedup_log(cluster_id,canonical_anime_id,method,members,created_at) "
            "VALUES(?,?,?,?,?)",
            (anime_id, anime_id, method,
             json.dumps([{"source": all_recs[i]["source"], "remote_id": all_recs[i]["remote_id"]}
                         for i in members_sorted], ensure_ascii=False), now()))
        if len(members) > 1:
            stats["merged_external"] += max(0, len(members) - 1)
        for i in members:
            rec = all_recs[i]
            url = None
            if rec["source"] == "anilist":
                url = f"https://anilist.co/anime/{rec['remote_id']}"
            elif rec["source"] == "kitsu":
                url = f"https://kitsu.app/anime/{rec['remote_id']}"
            elif rec["source"] == "shikimori":
                url = f"https://shikimori.one/animes/{rec['remote_id']}"
            elif rec["source"] == "wikidata":
                url = f"https://www.wikidata.org/wiki/{rec['remote_id']}"
            conn.execute(
                "INSERT OR REPLACE INTO anime_source(source,remote_id,anime_id,url,link_method,confidence) "
                "VALUES(?,?,?,?,?,?)",
                (rec["source"], rec["remote_id"], anime_id, url, method, CONF[method]),
            )
    conn.commit()
    cp_set(conn, "dedup_done", True)
    cp_set(conn, "anime_count", anime_id)
    log(conn, "dedup", f"clusters={stats['clusters']} multi_source={stats['multi_source']} "
                       f"methods={stats['method_counts']} tiers={stats['tiers']} "
                       f"merged_external={stats['merged_external']}")
    print(json.dumps(stats, indent=2))
    conn.close()
    return 0
