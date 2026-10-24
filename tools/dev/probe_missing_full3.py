import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect, CACHE_DIR
from src.sources.anilist import AniList
from src.config import load
from src.pipeline.enrich import tier_ids, _links

cfg = load()
conn = connect()
have = {r[0] for r in conn.execute(
    "select remote_id from raw_payload where source='anilist' and remote_kind='media_full'")}
wanted = set(_links(conn, "anilist")) & tier_ids(conn, config=cfg)
missing = [str(lid) for lid in wanted if str(lid) not in have]
light_have = {r[0] for r in conn.execute(
    "select remote_id from raw_payload where source='anilist' and remote_kind='media_light'")}
both = [x for x in missing if x in light_have]
print("missing:", len(missing), "| of those with media_light row:", len(both))
for rid in both[:10]:
    row = conn.execute("select payload->'$.title' as t from raw_payload where source='anilist' and remote_kind='media_light' and remote_id=?", (rid,)).fetchone()
    print(" ", rid, "->", row["t"] if row else None)
src = AniList(cfg["anilist"], CACHE_DIR, per_minute=cfg["anilist"]["per_minute"])
data = src.light([int(x) for x in both[:70]])
print("light() on 70 of them returned", len(data))