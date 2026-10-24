import sqlite3

c = sqlite3.connect(r"C:\Users\Umar\anime-text-dataset\data\anime.db", timeout=60)
c.execute("update checkpoint set value='5150', updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') where key='anilist_scan_upto'")
c.commit()
print("cp:", c.execute("select value from checkpoint where key='anilist_scan_upto'").fetchone()[0])
