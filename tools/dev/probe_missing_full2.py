import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
import requests

from src.db import connect, CACHE_DIR
from src.sources.anilist import AniList
from src.config import load
from src.pipeline.enrich import tier_ids, _links

cfg = load()
conn = connect()
have = {r[0] for r in conn.execute(
    "select remote_id from raw_payload where source='anilist' and remote_kind='media_full'")}
wanted = set(_links(conn, "anilist")) & tier_ids(conn, config=cfg)
missing = [lid for lid in wanted if str(lid) not in have]
src = AniList(cfg["anilist"], CACHE_DIR, per_minute=cfg["anilist"]["per_minute"])
print("tier anilist anime:", len(wanted), "| missing remote ids:", len(missing))
data = src.full(missing[:80])
print("requested 80, returned", len(data), "-> first sample:", [(m.get("id"), (m.get("title") or {}).get("romaji")) for m in data[:4]])