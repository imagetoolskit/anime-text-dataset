import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect, CACHE_DIR
from src.sources.anilist import AniList
from src.config import load
from src.pipeline.enrich import tier_ids, _links

cfg = load()
conn = connect()
src = AniList(cfg["anilist"], CACHE_DIR, per_minute=cfg["anilist"]["per_minute"])
have = {r[0] for r in conn.execute(
    "select remote_id from raw_payload where source='anilist' and remote_kind='media_full'")}
wanted = set(_links(conn, "anilist")) & tier_ids(conn, config=cfg)
missing = sorted(int(x) for x in wanted if str(x) not in have)
print("tier anilist ids:", len(wanted), "| missing:", len(missing))
sample = missing[:60]
data = src.full(sample)
got = {m["id"] for m in data}
print("requested", len(sample), "returned", len(data))
print("sample returned missing:", len(data))
print("first returned titles:", [(m.get("id"), (m.get("title") or {}).get("romaji")) for m in data[:5]])