import json
import re

from ..db import connect, cp_set, log

# AniList returns SCREAMING_SNAKE labels, Shikimori returns title case. Both are
# mapped onto the closed vocabulary in `src/validate/validators.py` so the same
# edge from two sources collapses into one row instead of duplicating.
RELATION_MAP = {
    "sequel": "SEQUEL",
    "prequel": "PREQUEL",
    "parent": "PARENT_STORY",
    "parent_story": "PARENT_STORY",
    "full_story": "FULL_STORY",
    "side_story": "SIDE_STORY",
    "spin_off": "SPIN_OFF",
    "alternative": "ALTERNATIVE_VERSION",
    "alternative_version": "ALTERNATIVE_VERSION",
    "alternative_setting": "ALTERNATIVE_SETTING",
    "summary": "SUMMARY",
    "adaptation": "ADAPTATION",
    "character": "CHARACTER",
    "same_series": "SAME_SERIES",
    "source": "SOURCE",
    "compilation": "COMPILATION",
    "contains": "CONTAINS",
    "other": "OTHER",
}


def canonical_relation(value) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return RELATION_MAP.get(key, "OTHER")


def run() -> int:
    conn = connect()
    conn.execute("DELETE FROM relationships")
    src_map = {r["remote_id"]: r["anime_id"]
               for r in conn.execute("select anime_id, remote_id from anime_source where source='anilist'")}

    # One row per (source work, target work, canonical relation). `sources` records
    # every provider that asserted the edge; a self-loop is never a valid edge and
    # is dropped rather than stored.
    edges: dict[tuple[int, int, str], dict] = {}

    def add(aid: int, other: int, relation, source: str, remote_id: str) -> None:
        if aid == other:
            return
        key = (aid, other, canonical_relation(relation))
        entry = edges.get(key)
        if entry is None:
            edges[key] = {"other_source": source, "other_remote_id": remote_id,
                          "sources": {source}}
        else:
            entry["sources"].add(source)

    cur = conn.execute("select remote_id, payload from raw_payload "
                       "where source='anilist' and remote_kind='media_full'")
    for row in cur:
        aid = src_map.get(row["remote_id"])
        if aid is None:
            continue
        p = json.loads(row["payload"])
        for edge in (p.get("relations") or {}).get("edges") or []:
            node = edge.get("node") or {}
            if not node.get("id"):
                continue
            # Only anime-to-anime edges: manga ids are a different namespace and
            # would collide with unrelated anime ids in anime_source.
            if node.get("type") not in (None, "ANIME"):
                continue
            other = src_map.get(str(node["id"]))
            if other is None:
                continue
            add(aid, other, edge.get("relationType"), "anilist", str(node["id"]))

    shi_map = {r["remote_id"]: r["anime_id"]
               for r in conn.execute("select anime_id, remote_id from anime_source where source='shikimori'")}
    cur = conn.execute("select remote_id, payload from raw_payload "
                       "where source='shikimori' and remote_kind='related'")
    for row in cur:
        aid = shi_map.get(row["remote_id"])
        if aid is None:
            continue
        for item in json.loads(row["payload"]):
            # Shikimori returns manga relations in the same list; those ids belong to
            # the manga namespace, so only `anime` entries are valid here.
            target = item.get("anime")
            if not target:
                continue
            other = shi_map.get(str(target.get("id")))
            if other is None:
                continue
            add(aid, other, item.get("relation"), "shikimori", str(target.get("id")))

    rows = [(aid, other, e["other_source"], e["other_remote_id"], relation,
             "+".join(sorted(e["sources"])))
            for (aid, other, relation), e in sorted(edges.items())]
    conn.executemany(
        "INSERT INTO relationships(anime_id,other_anime_id,other_source,other_remote_id,relation,source) "
        "VALUES(?,?,?,?,?,?)", rows)
    conn.commit()
    cp_set(conn, "relationships_done", True)
    log(conn, "relationships", f"rows={len(rows)}")
    print(f"relationships={len(rows)}")
    conn.close()
    return 0
