import random

from ..config import load
from ..db import connect, cp_set, log


def run() -> int:
    cfg = load()
    rng = random.Random(cfg["seed"])
    conn = connect()
    conn.execute("DELETE FROM splits")
    aids = [r[0] for r in conn.execute("select anime_id from anime order by anime_id")]
    rng.shuffle(aids)
    n = len(aids)
    n_train = int(n * 0.90)
    n_val = int(n * 0.05)
    rows = []
    for i, aid in enumerate(aids):
        if i < n_train:
            split = "train"
        elif i < n_train + n_val:
            split = "val"
        else:
            split = "test"
        rows.append((aid, split))
    conn.executemany("INSERT INTO splits(anime_id, split) VALUES(?,?)", rows)
    conn.commit()
    counts = dict(conn.execute("select split, count(*) from splits group by split"))
    cp_set(conn, "split_done", True)
    log(conn, "split", f"total={n} {counts}")
    print(f"splits: total={n} {counts}")
    conn.close()
    return 0
