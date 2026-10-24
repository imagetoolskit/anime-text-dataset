import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.validate.validators import _norm_title
from src.db import connect

c = connect()
rows = c.execute("select anime_id, coalesce(title_canonical, title_english), year, type from anime "
                 "where title_canonical is not null or title_english is not null").fetchall()
cnt = Counter()
for aid, t, y, ty in rows:
    nt = _norm_title(t)
    if nt:
        cnt[(nt, y)] += 1
for key, v in cnt.items():
    if v > 1:
        items = [(aid, t, y, ty) for aid, t, y, ty in rows if _norm_title(t) == key[0] and y == key[1]]
        for aid, t, y, ty in items:
            line = f"key={key} aid={aid} type={ty} title={t}"
            print(line.encode("ascii", "replace").decode())