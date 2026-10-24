import json
import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect

c = connect()
n = c.execute("select count(*) from raw_payload where source='kitsu' and remote_kind='episodes'").fetchone()[0]
print("raw episodes:", n)
keys = {r[0] for r in c.execute("select remote_id from anime_source where source='kitsu'")}
print("kitsu anime_source keys:", len(keys))
m = 0
miss = []
for row in c.execute("select payload from raw_payload where source='kitsu' and remote_kind='episodes' limit 50"):
    ep = json.loads(row["payload"])
    rel = (ep.get("relationships") or {}).get("media", {}).get("data") or {}
    rid = str(rel.get("id"))
    if rel.get("type") not in (None, "anime"):
        continue
    if rid in keys:
        m += 1
    else:
        miss.append(rid)
print("matched:", m, "missing sample:", miss[:8])