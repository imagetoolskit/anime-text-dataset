import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.validate.validators import _norm_title
from src.db import connect

c = connect()
cnt = Counter()
rows = c.execute("select anime_id, coalesce(title_canonical, title_english), year from anime "
                 "where title_canonical is not null or title_english is not null").fetchall()
for aid, t, y in rows:
    nt = _norm_title(t)
    if nt:
        cnt[(nt, y)] += 1
dups = {k: v for k, v in cnt.items() if v > 1}
print("non-empty dup groups:", len(dups))
for k, v in list(dups.items())[:10]:
    print("  ", repr(k), v)
print("total groups indexed:", len(cnt))