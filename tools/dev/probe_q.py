import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.validate.validators import _norm_title
from src.db import connect

c = connect()
for aid in (14525, 25843, 23485, 28289):
    t = c.execute("select coalesce(title_canonical, title_english) from anime where anime_id=?",
                  (aid,)).fetchone()[0]
    print(aid, "title_repr=", repr(t), "norm=", repr(_norm_title(t)))