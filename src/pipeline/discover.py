import json
import sqlite3
import sys
import time

from ..config import load
from ..db import CACHE_DIR, connect, cp_get, cp_set, log, now, upsert_raw
from ..sources.anilist import AniList
from ..sources.kitsu import Kitsu
from ..sources.shikimori import Shikimori
from ..sources.wikidata import Wikidata
from ..sources.ann import ANN

LICENSE_NOTES = {
    "anilist": "AniList public GraphQL API; data per AniList terms; retrieved via api docs.anilist.co",
    "kitsu": "Kitsu public JSON:API; data used under Kitsu's terms, which grant no redistribution; api docs at hummingbird-me.github.io/api-docs",
    "shikimori": "Shikimori public API; license/terms not located explicitly - license_uncertain",
    "wikidata": "Wikidata, CC0",
    "ann": "Anime News Network encyclopedia page; copyrighted content - license_uncertain, limited factual fields only",
}


def source_budget_h(cfg, name: str) -> float | None:
    cap_h = cfg.get("max_source_runtime_hours", {}).get(name)
    return cap_h


def expired(t0: float, cap_h: float | None) -> bool:
    return cap_h is not None and time.time() - t0 >= cap_h * 3600


def discover_anilist(limit: int | None = None) -> None:
    cfg = load()
    conn = connect()
    src = AniList(cfg["anilist"], CACHE_DIR, per_minute=cfg["anilist"]["per_minute"])
    max_id = cfg["anilist"]["max_id"]
    batch = cfg["anilist"]["light_batch"]
    start = cp_get(conn, "anilist_scan_upto", 0)
    done = 0
    t0 = time.time()
    completed = True
    for chunk_start in range(start, max_id, batch):
        ids = list(range(chunk_start + 1, min(chunk_start + batch, max_id) + 1))
        try:
            data = src.light(ids)
        except RuntimeError as exc:
            log(conn, "discovery", f"anilist chunk {chunk_start} failed: {exc}")
            completed = False
            break
        for media in data:
            upsert_raw(conn, "anilist", "media_light", media["id"], media,
                       url="https://graphql.anilist.co", license_note=LICENSE_NOTES["anilist"])
        done += len(ids)
        conn.commit()
        cp_set(conn, "anilist_scan_upto", chunk_start + batch)
        if chunk_start % (batch * cfg["checkpoint_interval"]) == 0:
            rate = done / max(1e-6, time.time() - t0)
            log(conn, "discovery",
                f"anilist upto {chunk_start + batch}/{max_id} ({rate:.0f} ids/s, "
                f"eta {((max_id - chunk_start) / max(rate, 1)) / 60:.0f} min)")
        if limit and done >= limit:
            completed = False
            break
        if expired(t0, source_budget_h(cfg, "anilist")):
            log(conn, "discovery", "anilist runtime budget reached; checkpoint saved; halting cleanly")
            completed = False
            break
    if completed:
        cp_set(conn, "anilist_scan_upto", max_id)
    log(conn, "discovery", f"anilist discovery finished: {done} ids in {(time.time() - t0) / 60:.1f} min "
                          f"stats={src.stats}")
    conn.close()


def discover_kitsu() -> None:
    cfg = load()
    conn = connect()
    src = Kitsu(cfg["kitsu"], CACHE_DIR, per_second=cfg["kitsu"]["per_second"])
    total = cp_get(conn, "kitsu_scan_total", None)
    offset = cp_get(conn, "kitsu_scan_upto", 0)
    limit = cfg["kitsu"]["page_limit"]
    t0 = time.time()
    while True:
        data = src.list_page(offset=offset, limit=limit)
        if not data:
            break
        for item in data:
            upsert_raw(conn, "kitsu", "anime", item["id"], item,
                       url=f"{src.base}/anime/{item['id']}", license_note=LICENSE_NOTES["kitsu"])
        if total is None:
            total = src.total_anime()
            cp_set(conn, "kitsu_scan_total", total)
            log(conn, "discovery", f"kitsu total anime = {total}")
        offset += len(data)
        conn.commit()
        cp_set(conn, "kitsu_scan_upto", offset)
        if len(data) < limit:
            break
        if offset % (limit * 20) == 0:
            log(conn, "discovery", f"kitsu offset {offset}/{total} ({(time.time() - t0) / 60:.1f} min)")
        if expired(t0, source_budget_h(cfg, "kitsu")):
            log(conn, "discovery", "kitsu runtime budget reached; checkpoint saved; halting cleanly")
            break
    log(conn, "discovery", f"kitsu discovery finished: {offset} rows, stats={src.stats}")
    conn.close()


def discover_shikimori() -> None:
    cfg = load()
    conn = connect()
    src = Shikimori(cfg["shikimori"], CACHE_DIR, per_second=cfg["shikimori"]["per_second"])
    page = cp_get(conn, "shikimori_scan_upto", 1)
    limit = cfg["shikimori"]["page_limit"]
    t0 = time.time()
    while True:
        data = src.list_page(page=page, limit=limit)
        if not data:
            break
        for item in data:
            upsert_raw(conn, "shikimori", "anime", item["id"], item,
                       url=f"{src.base}/animes/{item['id']}", license_note=LICENSE_NOTES["shikimori"])
        conn.commit()
        cp_set(conn, "shikimori_scan_upto", page + 1)
        if len(data) < limit:
            break
        if page % 40 == 0:
            log(conn, "discovery", f"shikimori page {page} ({(time.time() - t0) / 60:.1f} min)")
        if expired(t0, source_budget_h(cfg, "shikimori")):
            log(conn, "discovery", "shikimori runtime budget reached; checkpoint saved; halting cleanly")
            break
        page += 1
    log(conn, "discovery", f"shikimori discovery finished at page {page}, stats={src.stats}")
    conn.close()


def discover_wikidata() -> None:
    cfg = load()
    conn = connect()
    src = Wikidata(cfg["wikidata"], CACHE_DIR, per_second=cfg["wikidata"]["per_second"])
    rows = src.fetch_anime_items()
    for row in rows:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        upsert_raw(conn, "wikidata", "item", qid, row,
                   url=row["item"]["value"], license_note=LICENSE_NOTES["wikidata"])
    conn.commit()
    cp_set(conn, "wikidata_items", len(rows))
    log(conn, "discovery", f"wikidata finished: {len(rows)} items, stats={src.stats}")
    conn.close()


def discover_ann_sample() -> None:
    cfg = load()
    conn = connect()
    src = ANN(cfg["ann"], CACHE_DIR, per_second=cfg["ann"]["per_second"])
    import random
    rng = random.Random(cfg["seed"])
    ids = cp_get(conn, "ann_sample_ids", None)
    if ids is None:
        ids = sorted(rng.sample(range(1, cfg["ann"]["max_id"]), cfg["ann"]["sample_size"]))
        cp_set(conn, "ann_sample_ids", ids)
    start = cp_get(conn, "ann_sample_upto", 0)
    t0 = time.time()
    found = 0
    for i in range(start, len(ids)):
        aid = ids[i]
        try:
            page = src.fetch(aid)
        except RuntimeError as exc:
            log(conn, "discovery", f"ann id {aid} skipped: {exc}")
            conn.commit()
            continue
        if page:
            upsert_raw(conn, "ann", "page", aid, page,
                       url=f"{cfg['ann']['base']}?id={aid}",
                       license_note=LICENSE_NOTES["ann"])
            found += 1
        if i % 50 == 0:
            conn.commit()
            cp_set(conn, "ann_sample_upto", i)
            if expired(t0, source_budget_h(cfg, "ann")):
                log(conn, "discovery", "ann runtime budget reached; checkpoint saved; halting cleanly")
                break
    conn.commit()
    cp_set(conn, "ann_sample_upto", len(ids))
    log(conn, "discovery", f"ann sample finished: {found}/{len(ids)} pages, stats={src.stats}")
    conn.close()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m src.cli discover <anilist|kitsu|shikimori|wikidata|ann|all>")
        return 2
    what = argv[1]
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    if what == "anilist":
        discover_anilist(limit)
    elif what == "kitsu":
        discover_kitsu()
    elif what == "shikimori":
        discover_shikimori()
    elif what == "wikidata":
        discover_wikidata()
    elif what == "ann":
        discover_ann_sample()
    elif what == "all":
        discover_anilist(limit)
        discover_kitsu()
        discover_shikimori()
        discover_wikidata()
        discover_ann_sample()
    else:
        print(f"unknown target: {what}")
        return 2
    return 0
