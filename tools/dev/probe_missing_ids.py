import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
import requests

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
tests = missing[:5]
Q = "query($id:Int){Media(id:$id){id type title{romaji}}}"
for tid in tests:
    r = requests.post("https://graphql.anilist.co", json={"query": Q, "variables": {"id": tid}}, timeout=60)
    body = r.json().get("data", {}).get("Media")
    print(f"id {tid}: {body.get('type') if body else None} - {body.get('title',{}).get('romaji') if body else None}")