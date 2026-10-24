from ..db import connect, cp_set, log

# Only relations that imply the works belong to one continuous franchise.
# ADAPTATION and CHARACTER edges are deliberately excluded: they link works that
# merely share a source or a cameo, which previously merged all of Gundam,
# Cowboy Bebop and Lodoss into one "franchise".
LINK_RELS = {"SEQUEL", "PREQUEL", "PARENT_STORY", "SIDE_STORY", "SPIN_OFF",
             "ALTERNATIVE_SETTING", "ALTERNATIVE_VERSION", "SUMMARY", "FULL_STORY"}


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def run() -> int:
    conn = connect()
    conn.execute("DELETE FROM franchises")
    uf = UnionFind()
    edges = 0
    for r in conn.execute(
            "select anime_id, other_anime_id, relation from relationships "
            "where other_anime_id is not null"):
        if r["relation"] in LINK_RELS:
            uf.union(r["anime_id"], r["other_anime_id"])
            edges += 1
    roots = {}
    franchises = 0
    rows = []
    for (aid,) in conn.execute("select anime_id from anime"):
        root = uf.find(aid)
        fid = roots.get(root)
        if fid is None:
            franchises += 1
            fid = franchises
            roots[root] = fid
        rows.append((aid, fid))
    conn.executemany("INSERT OR REPLACE INTO franchises(anime_id, franchise_id) VALUES(?,?)", rows)
    conn.commit()
    members = conn.execute(
        "select franchise_id, count(*) c from franchises group by franchise_id having c > 1").fetchall()
    cp_set(conn, "franchise_done", True)
    log(conn, "franchise", f"edges={edges} franchises={franchises} multi_member={len(members)}")
    print(f"franchises={franchises} edges={edges}")
    conn.close()
    return 0