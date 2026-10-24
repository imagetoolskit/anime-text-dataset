import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
from src.db import connect

c = connect()
n = c.execute("delete from raw_payload where (source='anilist' and remote_kind='media_full') "
              "or (source='shikimori' and remote_kind in ('detail','roles','related'))").rowcount
print("deleted polluted raw rows:", n)

tables = ["anime", "anime_source", "dedup_log", "alt_titles", "anime_genres", "anime_themes",
          "anime_studios", "genres", "themes", "studios", "characters", "staff", "provenance",
          "relationships", "descriptions", "qa_pairs", "instructions", "franchises", "rag_chunks",
          "splits", "quality_validation"]
for t in tables:
    c.execute(f"delete from {t}")
print("wiped derived tables")

keys = ["anime_count", "entities_done", "enrich_anilist_done", "enrich_shikimori_done",
        "shikimori_roles_done", "shikimori_related_done", "kitsu_episodes_anime_done",
        "kitsu_episodes_done"]
c.execute("delete from checkpoint where key in (%s)" % ",".join("?" * len(keys)), keys)
print("reset checkpoints")
c.commit()

for src, kind in (("anilist", "media_light"), ("kitsu", "anime"), ("kitsu", "episodes"),
                  ("shikimori", "anime"), ("wikidata", "item"), ("ann", "page")):
    n = c.execute("select count(*) from raw_payload where source=? and remote_kind=?", (src, kind)).fetchone()[0]
    print(f"  kept {src} {kind}: {n}")