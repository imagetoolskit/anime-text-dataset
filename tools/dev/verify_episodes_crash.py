import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect, CACHE_DIR
from src.sources.kitsu import Kitsu
from src.config import load
from src.pipeline.enrich import tier_ids, _links

cfg = load()
conn = connect()
src = Kitsu(cfg["kitsu"], CACHE_DIR, per_second=cfg["kitsu"]["per_second"])
kitsu_links = _links(conn, "kitsu")
tierset = tier_ids(conn, config=cfg)
anime_ids = sorted(t for t in tierset if t in kitsu_links)
print("total anime:", len(anime_ids))
for idx in range(6400, min(6420, len(anime_ids))):
    aid = anime_ids[idx]
    med = int(kitsu_links[aid])
    print(f"[{idx}] aid={aid} med={med}", flush=True)
    eps = src.episodes(med, 0, 10)
    print("   ->", len(eps) if eps is not None else None)