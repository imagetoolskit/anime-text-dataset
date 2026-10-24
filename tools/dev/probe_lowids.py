import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
import json

from src.db import connect

c = connect()
for rid in ("1", "2", "3", "4", "9", "10", "21898"):
    row = c.execute("select payload from raw_payload where source='anilist' and remote_kind='media_light' and remote_id=?",
                    (rid,)).fetchone()
    rs = c.execute("select anime_id from anime_source where source='anilist' and remote_id=?", (rid,)).fetchone()
    print(f"id {rid}: media_light={'yes' if row else 'NO'} anime_source={rs['anime_id'] if rs else None}",
          (json.loads(row['payload']).get('title', {}).get('romaji') if row else ''))