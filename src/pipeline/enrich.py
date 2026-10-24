"""Enrichment: fetch detailed records for the depth tier."""

import math
import time

from ..config import load
from ..db import CACHE_DIR, connect, cp_set, log, now, upsert_raw
from ..sources.anilist import AniList
from ..sources.kitsu import Kitsu
from ..sources.shikimori import Shikimori
from .discover import LICENSE_NOTES, expired, source_budget_h

TIER_FRACTION = 0.2


def tier_ids(conn, fraction: float = TIER_FRACTION, config: dict | None = None) -> set[int]:
    """Depth tier: roughly the top `fraction` of the canonical anime set, ranked by
    mean score (cross-source count/popularity scales are not comparable), then
    favourites, then id. All anime when the set is small."""
    cfg = config or load()
    override = cfg.get("enrichment_tier", {})
    if override.get("all"):
        return {r[0] for r in conn.execute("select anime_id from anime")}
    if override.get("fraction"):
        fraction = override["fraction"]
    rows = conn.execute(
        "select anime_id, mean_score, favourites from anime "
        "order by coalesce(mean_score, 0) desc, coalesce(favourites, 0) desc, anime_id"
    ).fetchall()
    if not rows:
        return set()
    keep = max(1, math.ceil(len(rows) * fraction))
    if override.get("min_count"):
        keep = max(keep, override["min_count"])
    return {r[0] for r in rows[:keep]}


def _links(conn, source: str) -> dict[int, str]:
    return {r[0]: r[1] for r in conn.execute(
        "select anime_id, remote_id from anime_source where source=?", (source,))}


def _remote_ids(conn, source: str) -> list[str]:
    return sorted(int(r[0]) for r in conn.execute(
        "select distinct remote_id from anime_source where source=?", (source,)))


def enrich_anilist(limit_batches: int | None = None, all_ids: bool = False) -> int:
    cfg = load()
    conn = connect()
    src = AniList(cfg["anilist"], CACHE_DIR, per_minute=cfg["anilist"]["per_minute"])
    batch = cfg["anilist"]["full_batch"]
    cap_h = source_budget_h(cfg, "enrich_anilist") or source_budget_h(cfg, "anilist")
    t0 = time.time()
    links = _links(conn, "anilist")
    if all_ids:
        wanted = set(links.values())
    else:
        tier = tier_ids(conn, config=cfg)
        wanted = {links[a] for a in tier if a in links}
    if not wanted:
        return 0
    todo = sorted(int(r) for r in wanted)
    if todo:
        have = {r[0] for r in conn.execute(
            "select remote_id from raw_payload where source='anilist' and remote_kind='media_full'")}
        todo = [x for x in todo if str(x) not in have]
    log(conn, "enrich", f"anilist full: {len(todo)} anime to enrich (tier={'all' if all_ids else '20%'})")
    done = 0
    batches = 0
    for i in range(0, len(todo), batch):
        ids = todo[i:i + batch]
        try:
            data = src.full(ids)
        except RuntimeError as exc:
            log(conn, "enrich", f"anilist full batch failed: {exc}")
            continue
        for media in data:
            upsert_raw(conn, "anilist", "media_full", media["id"], media,
                       url=f"https://anilist.co/anime/{media['id']}",
                       license_note=LICENSE_NOTES["anilist"])
        conn.commit()
        done += len(ids)
        batches += 1
        if batches % 100 == 0:
            log(conn, "enrich", f"anilist full {done}/{len(todo)} ({src.stats})")
        if expired(t0, cap_h):
            break
        if limit_batches and batches >= limit_batches:
            break
    cp_set(conn, "enrich_anilist_done", done)
    log(conn, "enrich", f"anilist full finished: {done} anime, {src.stats}")
    conn.close()
    return done


def enrich_shikimori(limit: int | None = None, all_ids: bool = False) -> int:
    cfg = load()
    conn = connect()
    src = Shikimori(cfg["shikimori"], CACHE_DIR, per_second=cfg["shikimori"]["per_second"])
    cap_h = source_budget_h(cfg, "enrich_shikimori") or source_budget_h(cfg, "shikimori")
    t0 = time.time()
    links = _links(conn, "shikimori")
    if all_ids:
        wanted = set(links.values())
    else:
        tier = tier_ids(conn, config=cfg)
        wanted = {links[a] for a in tier if a in links}
    todo = sorted(int(x) for x in wanted)
    if todo:
        have = {r[0] for r in conn.execute(
            "select remote_id from raw_payload where source='shikimori' and remote_kind='detail'")}
        todo = [x for x in todo if str(x) not in have]
    log(conn, "enrich", f"shikimori detail: {len(todo)} to enrich (tier={'all' if all_ids else '20%'})")
    done = 0
    for rid in todo:
        try:
            detail = src.detail(rid)
        except RuntimeError as exc:
            log(conn, "enrich", f"shikimori detail {rid} failed: {exc}")
            continue
        upsert_raw(conn, "shikimori", "detail", rid, detail,
                   url=f"https://shikimori.one/animes/{rid}",
                   license_note=LICENSE_NOTES["shikimori"])
        done += 1
        if done % 100 == 0:
            conn.commit()
            if done % 1000 == 0:
                log(conn, "enrich", f"shikimori detail {done}/{len(todo)} ({src.stats})")
            if expired(t0, cap_h):
                break
        if limit and done >= limit:
            break
    conn.commit()
    cp_set(conn, "enrich_shikimori_done", done)
    log(conn, "enrich", f"shikimori detail finished: {done}, {src.stats}")
    conn.close()
    return done


def enrich_episodes(all_ids: bool = False) -> int:
    cfg = load()
    conn = connect()
    src = Kitsu(cfg["kitsu"], CACHE_DIR, per_second=cfg["kitsu"]["per_second"])
    cap_h = source_budget_h(cfg, "enrich_episodes") or source_budget_h(cfg, "kitsu")
    t0 = time.time()
    kitsu_links = _links(conn, "kitsu")
    tierset = tier_ids(conn, config=cfg)
    anime_ids = list(kitsu_links) if all_ids else sorted(t for t in tierset if t in kitsu_links)
    # Skip anime whose episode payloads were already collected completely.
    have_media = {r[0] for r in conn.execute(
        "select distinct json_extract(payload,'$._media_id') from raw_payload "
        "where source='kitsu' and remote_kind='episodes'")}
    anime_ids = [aid for aid in anime_ids if str(kitsu_links[aid]) not in have_media]
    # No index checkpoint here: the completed set is derived from the payloads
    # themselves (`have_media`), so a re-run resumes correctly even when the todo
    # list changes length. An index checkpoint would skip and re-fetch the wrong
    # anime as soon as a few payloads arrived.
    total_ep = 0
    limit = cfg["kitsu"]["page_limit"]
    for idx, aid in enumerate(anime_ids):
        med = int(kitsu_links[aid])
        offset = 0
        while True:
            eps = src.episodes(med, offset, limit)
            if not eps:
                break
            for ep in eps:
                ep["_media_id"] = med
                upsert_raw(conn, "kitsu", "episodes", ep.get("id"), ep,
                           url=f"{src.base}/episodes/{ep.get('id')}",
                           license_note=LICENSE_NOTES["kitsu"])
                total_ep += 1
            offset += len(eps)
            if len(eps) < limit:
                break
        if idx % 100 == 0 and idx > 0:
            conn.commit()
            log(conn, "enrich", f"kitsu episodes {idx}/{len(anime_ids)} anime eps={total_ep} ({src.stats})")
        if expired(t0, cap_h):
            break
    conn.commit()
    cp_set(conn, "kitsu_episodes_done", total_ep)
    log(conn, "enrich", f"kitsu episodes finished anime={len(anime_ids)} eps={total_ep} ({src.stats})")
    conn.close()
    return total_ep


def enrich_shikimori_roles(all_ids: bool = False) -> int:
    cfg = load()
    conn = connect()
    src = Shikimori(cfg["shikimori"], CACHE_DIR, per_second=cfg["shikimori"]["per_second"])
    cap_h = source_budget_h(cfg, "enrich_roles") or source_budget_h(cfg, "shikimori")
    t0 = time.time()
    links = _links(conn, "shikimori")
    if all_ids:
        wanted = set(links.values())
    else:
        tier = tier_ids(conn, config=cfg)
        wanted = {links[a] for a in tier if a in links}
    todo = sorted(int(x) for x in wanted)
    if todo:
        valid = {r[0] for r in conn.execute(
            "select remote_id from raw_payload where source='shikimori' and remote_kind='detail'")}
        have = {r[0] for r in conn.execute(
            "select remote_id from raw_payload where source='shikimori' and remote_kind='roles'")}
        todo = [x for x in todo if str(x) in valid and str(x) not in have]
    log(conn, "enrich", f"shikimori roles: {len(todo)} to fetch (tier={'all' if all_ids else '20%'})")
    done = 0
    for rid in todo:
        try:
            roles = src.roles(rid)
        except RuntimeError as exc:
            log(conn, "enrich", f"shikimori roles {rid} failed: {exc}")
            continue
        upsert_raw(conn, "shikimori", "roles", rid, roles,
                   url=f"https://shikimori.one/animes/{rid}/roles",
                   license_note=LICENSE_NOTES["shikimori"])
        done += 1
        if done % 100 == 0:
            conn.commit()
            if done % 2000 == 0:
                log(conn, "enrich", f"shikimori roles {done}/{len(todo)} ({src.stats})")
            if expired(t0, cap_h):
                break
    conn.commit()
    cp_set(conn, "shikimori_roles_done", done)
    log(conn, "enrich", f"shikimori roles finished: {done}, {src.stats}")
    conn.close()
    return done


def enrich_shikimori_related(all_ids: bool = False) -> int:
    cfg = load()
    conn = connect()
    src = Shikimori(cfg["shikimori"], CACHE_DIR, per_second=cfg["shikimori"]["per_second"])
    cap_h = source_budget_h(cfg, "enrich_related") or source_budget_h(cfg, "shikimori")
    t0 = time.time()
    links = _links(conn, "shikimori")
    if all_ids:
        wanted = set(links.values())
    else:
        tier = tier_ids(conn, config=cfg)
        wanted = {links[a] for a in tier if a in links}
    todo = sorted(int(x) for x in wanted)
    if todo:
        valid = {r[0] for r in conn.execute(
            "select remote_id from raw_payload where source='shikimori' and remote_kind='detail'")}
        have = {r[0] for r in conn.execute(
            "select remote_id from raw_payload where source='shikimori' and remote_kind='related'")}
        todo = [x for x in todo if str(x) in valid and str(x) not in have]
    log(conn, "enrich", f"shikimori related: {len(todo)} to fetch (tier={'all' if all_ids else '20%'})")
    done = 0
    for rid in todo:
        try:
            related = src.related(rid)
        except RuntimeError as exc:
            log(conn, "enrich", f"shikimori related {rid} failed: {exc}")
            continue
        upsert_raw(conn, "shikimori", "related", rid, related,
                   url=f"https://shikimori.one/animes/{rid}/related",
                   license_note=LICENSE_NOTES["shikimori"])
        done += 1
        if done % 100 == 0:
            conn.commit()
            if done % 2000 == 0:
                log(conn, "enrich", f"shikimori related {done}/{len(todo)} ({src.stats})")
            if expired(t0, cap_h):
                break
    conn.commit()
    cp_set(conn, "shikimori_related_done", done)
    log(conn, "enrich", f"shikimori related finished: {done}, {src.stats}")
    conn.close()
    return done


def main(argv: list[str]) -> int:
    target = argv[1] if len(argv) > 1 else "anilist"
    all_ids = "--all" in argv
    if target == "anilist":
        enrich_anilist(all_ids=all_ids)
    elif target == "shikimori":
        enrich_shikimori(all_ids=all_ids)
    elif target == "episodes":
        enrich_episodes(all_ids=all_ids)
    elif target == "roles":
        enrich_shikimori_roles(all_ids=all_ids)
    elif target == "related":
        enrich_shikimori_related(all_ids=all_ids)
    elif target == "all":
        enrich_anilist(all_ids=all_ids)
        enrich_shikimori(all_ids=all_ids)
        enrich_episodes(all_ids=all_ids)
        enrich_shikimori_roles(all_ids=all_ids)
        enrich_shikimori_related(all_ids=all_ids)
    else:
        print(f"unknown target: {target}")
        return 2
    return 0
