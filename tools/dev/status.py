import sqlite3
c = sqlite3.connect(r"C:\Users\Umar\anime-text-dataset\data\anime.db")
n = c.execute("select count(*) from raw_payload where source='anilist' and remote_kind='media_light'").fetchone()[0]
print("media_light rows:", n)
for row in c.execute("select key, value, updated_at from checkpoint"):
    print("cp:", row)
for row in c.execute("select ts, phase, message from run_log order by id desc limit 5"):
    print("log:", row)
