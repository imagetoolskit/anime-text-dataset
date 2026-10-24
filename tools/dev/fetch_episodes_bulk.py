import sys
import time

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.config import load
from src.db import connect, cp_set, log, now
from src.pipeline.enrich import upsert_raw, LICENSE_NOTES
from src.sources.kitsu import Kitsu

CACHE_DIR = r"C:\Users\Umar\anime-text-dataset\data\cache"

cfg = load()
conn = connect()
src = Kitsu(cfg["kitsu"], CACHE_DIR, per_second=cfg["kitsu"]["per_second"])
kitsu_map = {r["remote_id"] for r in conn.execute("select remote_id from anime_source where source='kitsu'")}
keep = 0
offset = 0
limit = 500
while True:
    eps = src.episodes_all(offset, limit)
    if not eps:
        break
    for ep in eps:
        rel = ((ep.get("relationships") or {}).get("media") or {}).get("data") or {}
        if rel.get("type") not in (None, "anime"):
            continue
        if str(rel.get("id")) not in kitsu_map:
            continue
        upsert_raw(conn, "kitsu", "episodes", ep.get("id"), ep,
                   url=f"{src.base}/episodes/{ep.get('id')}",
                   license_note=LICENSE_NOTES["kitsu"])
        keep += 1
    offset += len(eps)
    if len(eps) < limit:
        break
    if offset % 5000 < limit:
        conn.commit()
        log(conn, "enrich", f"episodes bulk offset={offset} keep={keep} ({src.stats})")
        print(f"offset={offset} keep={keep}")
    if keep and keep % 20000 == 0:
        conn.commit()
conn.commit()
cp_set(conn, "kitsu_episodes_anime_done", 6605)
cp_set(conn, "kitsu_episodes_done", keep)
log(conn, "enrich", f"episodes bulk finished offset={offset} keep={keep} ({src.stats})")
conn.close()
print(f"DONE keep={keep} offset={offset}")