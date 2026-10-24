"""Refill pass: fetch per-title detail records for works that still lack a
synopsis (and therefore duration, age rating, season, score etc. sourced from
detail endpoints), using live APIs. Hybrid provider pass: Shikimori detail,
AniList full media, then Kitsu detail, resumable and idempotent.

Fetched payloads are stored with the standard remote_kinds (`detail`,
`media_full`, `anime`) so upstream passers (entities, relationships, backfill)
reuse them. After the fetch loop the backfill merge runs again to fold the new
fields into canonical anime rows with provenance.

Usage:
    python -m src.cli refill            # run all sources until budget exhausted
    python -m src.cli refill shikimori  # a single source
"""
from __future__ import annotations

import json
import time

from ..config import load
from ..db import CACHE_DIR, connect, cp_set, log, upsert_raw
from ..sources.anilist import AniList
from ..sources.kitsu import Kitsu
from ..sources.shikimori import Shikimori
from .backfill import run as backfill_run
from .discover import LICENSE_NOTES, expired, source_budget_h


def _worklist(conn, source: str) -> list[tuple[int, str]]:
    """(anime_id, remote_id) for works missing a synopsis with a link to source."""
    marks = "select anime_id from anime where synopsis is null or trim(synopsis)=''"
    want = {r[0] for r in conn.execute(marks)}
    if not want:
        return []
    ph = ",".join("?" * len(want))
    ids = list(want)
    ask = f"select anime_id, remote_id from anime_source where anime_id in ({ph}) and source=?"
    return [(r["anime_id"], str(r["remote_id"])) for r in conn.execute(ask, ids + [source])]


def _stored(conn, source: str, kind: str) -> set[str]:
    return {str(r[0]) for r in conn.execute(
        "select remote_id from raw_payload where source=? and remote_kind=?", (source, kind))}


def _refill_shikimori() -> int:
    cfg = load()
    conn = connect()
    src = Shikimori(cfg["shikimori"], CACHE_DIR, per_second=cfg["shikimori"]["per_second"])
    cap_h = source_budget_h(cfg, "refill_shikimori") or source_budget_h(cfg, "shikimori")
    t0 = time.time()
    done = _stored(conn, "shikimori", "detail")
    pairs = [(a, r) for a, r in _worklist(conn, "shikimori") if r not in done]
    log(conn, "refill", f"shikimori detail: {len(pairs)} to fetch")
    n = 0
    for aid, rid in pairs:
        try:
            detail = src.detail(int(rid))
        except RuntimeError as exc:
            log(conn, "refill", f"shikimori detail {rid} failed: {exc}")
            continue
        if not isinstance(detail, dict) or detail.get("id") is None:
            continue
        upsert_raw(conn, "shikimori", "detail", rid, detail,
                   url=f"https://shikimori.one/animes/{rid}",
                   license_note=LICENSE_NOTES["shikimori"])
        n += 1
        if n % 100 == 0:
            conn.commit()
            log(conn, "refill", f"shikimori detail {n}/{len(pairs)} ({src.stats})")
            if expired(t0, cap_h):
                break
    conn.commit()
    cp_set(conn, "refill_shikimori_done", n)
    log(conn, "refill", f"shikimori detail finished: {n}, {src.stats}")
    conn.close()
    return n


def _refill_anilist() -> int:
    cfg = load()
    conn = connect()
    src = AniList(cfg["anilist"], CACHE_DIR, per_minute=cfg["anilist"]["per_minute"])
    cap_h = source_budget_h(cfg, "refill_anilist") or source_budget_h(cfg, "anilist")
    t0 = time.time()
    have = _stored(conn, "anilist", "media_full")
    seen = set()
    todo = []
    for aid, rid in _worklist(conn, "anilist"):
        if rid in have or rid in seen:
            continue
        seen.add(rid)
        todo.append((aid, int(rid)))
    log(conn, "refill", f"anilist full: {len(todo)} to fetch")
    batch = cfg["anilist"]["full_batch"]
    n = 0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        ids = [r for _, r in chunk]
        try:
            data = src.full(ids)
        except RuntimeError as exc:
            log(conn, "refill", f"anilist full batch failed: {exc}")
            continue
        for media in data:
            upsert_raw(conn, "anilist", "media_full", media["id"], media,
                       url=f"https://anilist.co/anime/{media['id']}",
                       license_note=LICENSE_NOTES["anilist"])
        conn.commit()
        n += len(chunk)
        if n % 450 == 0:
            log(conn, "refill", f"anilist full {n}/{len(todo)} ({src.stats})")
        if expired(t0, cap_h):
            break
    conn.commit()
    cp_set(conn, "refill_anilist_done", n)
    log(conn, "refill", f"anilist full finished: {n}, {src.stats}")
    conn.close()
    return n


def _refill_kitsu() -> int:
    cfg = load()
    conn = connect()
    src = Kitsu(cfg["kitsu"], CACHE_DIR, per_second=cfg["kitsu"]["per_second"])
    cap_h = source_budget_h(cfg, "refill_kitsu") or source_budget_h(cfg, "kitsu")
    t0 = time.time()
    done = _stored(conn, "kitsu", "anime")
    pairs = [(a, r) for a, r in _worklist(conn, "kitsu") if r not in done]
    log(conn, "refill", f"kitsu detail: {len(pairs)} to fetch")
    n = 0
    for aid, rid in pairs:
        try:
            detail = src.detail(int(rid))
        except RuntimeError as exc:
            log(conn, "refill", f"kitsu detail {rid} failed: {exc}")
            continue
        if not isinstance(detail, dict):
            continue
        upsert_raw(conn, "kitsu", "anime", rid, detail,
                   url=f"{src.base}/anime/{rid}",
                   license_note=LICENSE_NOTES["kitsu"])
        n += 1
        if n % 50 == 0:
            conn.commit()
            log(conn, "refill", f"kitsu detail {n}/{len(pairs)} ({src.stats})")
            if expired(t0, cap_h):
                break
    conn.commit()
    cp_set(conn, "refill_kitsu_done", n)
    log(conn, "refill", f"kitsu detail finished: {n}, {src.stats}")
    conn.close()
    return n


def main(argv: list[str]) -> int:
    target = argv[1] if len(argv) > 1 else "all"
    if target in ("all", "shikimori"):
        _refill_shikimori()
    if target in ("all", "anilist"):
        _refill_anilist()
    if target in ("all", "kitsu"):
        _refill_kitsu()
    backfill_run()
    return 0
