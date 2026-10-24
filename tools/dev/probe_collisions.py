import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect
from collections import defaultdict

def norm(t):
    import unicodedata
    t = unicodedata.normalize("NFKC", (t or "")).casefold()
    for ch in "·・:：!！?？,，.。\"'“”‘’()[]{}<>-–—_ ":
        t = t.replace(ch, "")
    return t.strip()

c = connect()
rows = c.execute("select anime_id, coalesce(title_canonical, title_english), year, type from anime "
                 "where title_canonical is not null or title_english is not null").fetchall()
g = defaultdict(list)
for aid, t, y, ty in rows:
    g[(norm(t), y)].append((aid, t, y, ty))
dups = {k: v for k, v in g.items() if len(v) > 1}
print("collision groups:", len(dups))
for key, items in dups.items():
    for it in items:
        line = f"  key={key} aid={it[0]} type={it[3]} title={it[1]}"
        print(line.encode("ascii", "replace").decode())