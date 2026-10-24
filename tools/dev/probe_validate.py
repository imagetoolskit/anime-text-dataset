import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect

c = connect()
n = c.execute("select count(*) from anime where title_canonical is null and title_english is null").fetchone()[0]
print("anime missing all titles:", n)
for r in c.execute("select anime_id, title_canonical, title_english, year, quality_tier from anime "
                   "where title_canonical is null and title_english is null limit 10"):
    print("  ", r)
rows = c.execute("select t1 from (select anime_id, coalesce(nullif(title_canonical,''),title_english) t1, "
                 "coalesce(nullif(title_canonical,''),title_english) t2, year y from anime "
                 "where title_canonical is not null or title_english is not null) "
                 "group by lower(t1), y having count(*)>1 limit 20").fetchall()
print("sample title+y collisions (rough):", len(rows))
for r in rows:
    print("  ", r[0])