import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect

c = connect()
n = c.execute(
    "select count(*) from anime_source where source='anilist' and remote_id not in "
    "(select remote_id from raw_payload where source='anilist' and remote_kind='media_light')").fetchone()[0]
print("anilist links WITHOUT media_light row:", n)
row = c.execute(
    "select remote_id from anime_source where source='anilist' and remote_id not in "
    "(select remote_id from raw_payload where source='anilist' and remote_kind='media_light') limit 8").fetchall()
print("sample:", [r[0] for r in row])