import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect

c = connect()
for t in ["alt_titles", "anime_genres", "anime_themes", "anime_studios", "genres", "themes",
          "studios", "characters", "staff", "episodes", "provenance", "relationships",
          "descriptions", "qa_pairs", "instructions", "franchises", "rag_chunks", "splits",
          "quality_validation"]:
    c.execute(f"delete from {t}")
for k in c.execute("select key from checkpoint").fetchall():
    if k[0] != "anime_count":
        c.execute("delete from checkpoint where key=?", (k[0],))
c.commit()
print("wipe ok; anime:", c.execute("select count(*) from anime").fetchone()[0])