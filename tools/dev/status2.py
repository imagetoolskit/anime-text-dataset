import sqlite3

c = sqlite3.connect(r"C:\Users\Umar\anime-text-dataset\data\anime.db")
q = lambda s: c.execute(s).fetchone()[0]
print("anilist media_light:", q("select count(*) from raw_payload where source='anilist' and remote_kind='media_light'"))
print("kitsu anime:", q("select count(*) from raw_payload where source='kitsu' and remote_kind='anime'"))
print("shikimori anime:", q("select count(*) from raw_payload where source='shikimori' and remote_kind='anime'"))
print("shikimori detail:", q("select count(*) from raw_payload where source='shikimori' and remote_kind='detail'"))
print("ann page:", q("select count(*) from raw_payload where source='ann' and remote_kind='page'"))
print("wikidata item:", q("select count(*) from raw_payload where source='wikidata' and remote_kind='item'"))
for r in c.execute("select key, value, updated_at from checkpoint order by key"):
    if not r[0].startswith("ann_sample_ids"):
        print("cp:", r[0], "=", r[1], r[2])
