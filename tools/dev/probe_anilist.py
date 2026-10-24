import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect

c = connect()
n_full = c.execute("select count(*) from raw_payload where source='anilist' and remote_kind='media_full'").fetchone()[0]
n_src = c.execute("select count(*) from anime_source where source='anilist'").fetchone()[0]
n_matched = c.execute(
    "select count(*) from raw_payload p where p.source='anilist' and p.remote_kind='media_full' "
    "and exists (select 1 from anime_source s where s.source='anilist' and s.remote_id=p.remote_id)").fetchone()[0]
print("media_full raw:", n_full)
print("anilist anime_source:", n_src)
print("matched:", n_matched)
row = c.execute("select remote_id, payload from raw_payload where source='anilist' and remote_kind='media_full' order by rowid desc limit 1").fetchone()
if row:
    import json
    p = json.loads(row["payload"])
    print("sample remote_id:", row["remote_id"], "| payload id:", p.get("id"), "| title:", (p.get("title") or {}).get("romaji"))
print("anime rows:", c.execute("select count(*) from anime").fetchone()[0])
print("cp enrich_anilist_done:", c.execute("select value from checkpoint where key='enrich_anilist_done'").fetchone()["value"])