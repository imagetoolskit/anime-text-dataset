import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect

c = connect()
n = c.execute("delete from raw_payload where source='kitsu' and remote_kind='episodes'").rowcount
c.execute("delete from checkpoint where key in ('kitsu_episodes_anime_done','kitsu_episodes_done')")
c.execute("delete from episodes")
c.commit()
print("deleted partial raw episodes:", n)