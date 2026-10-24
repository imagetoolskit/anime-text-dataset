import json
import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect

c = connect()
wd = c.execute("select s.remote_id, s.anime_id from anime_source s "
               "join anime a on a.anime_id=s.anime_id "
               "where a.title_canonical is null and a.title_english is null and s.source='wikidata' "
               "limit 8").fetchall()
for rid, aid in wd:
    p = json.loads(c.execute("select payload from raw_payload where source='wikidata' and remote_kind='item' and remote_id=?",
                             (rid,)).fetchone()[0])
    keys = {k for k in p}
    labels = {k: v for k, v in p.items() if k.lower().startswith("enlabel") or "label" in k.lower()}
    lab_val = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in labels.items()}
    print(f"aid={aid} qid={rid} keys={len(keys)} labels={lab_val}")

print("---- the 3 title+y collisions ----")
rows = c.execute(
    "select anime_id, coalesce(nullif(title_canonical,''),title_english) t, year, type, quality_tier "
    "from anime where title_canonical is not null or title_english is not null").fetchall()
from collections import defaultdict
g = defaultdict(list)
for aid, t, y, ty, tier in rows:
    key = (t.replace("\u221e", "*"), y)
    g[key].append((aid, t, y, ty, tier))
for key, items in g.items():
    if len(items) > 1:
        for it in items:
            print(" ", key, it)