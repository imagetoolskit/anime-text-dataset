"""Generate reports/data_profile.json — a statistical profile of the exported dataset.

Streams each JSONL export once and records counts, distributions and
coverage rates in a stable JSON shape consumed by docs/explore.html.

Usage:
    python scripts/data_profile.py [--out reports/data_profile.json]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports")

sys.path.insert(0, ROOT)
from src.config import VERSION  # noqa: E402  (single source of the release version)


def load_lines(name: str) -> list[dict]:
    path = os.path.join(EXPORTS, f"{name}.jsonl")
    records: list[dict] = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def q(series: list[float]) -> dict | None:
    if not series:
        return None
    series = sorted(series)
    n = len(series)
    lo, med, hi = statistics.quantiles(series, n=4, method="inclusive")
    return {
        "count": n,
        "min": round(min(series), 4),
        "q1": round(lo, 4),
        "median": round(med, 4),
        "q3": round(hi, 4),
        "max": round(max(series), 4),
        "mean": round(sum(series) / n, 4),
    }


def lens(values: list[str]) -> dict | None:
    return q([len(v) for v in values])


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def top(c: Counter, n: int = 20) -> list[dict]:
    return [{"value": k, "count": v} for k, v in c.most_common(n)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "reports", "data_profile.json"))
    args = ap.parse_args()

    anime = load_lines("anime")
    profile: dict = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": VERSION,
    }

    years = Counter()
    types = Counter()
    statuses = Counter()
    seasons = Counter()
    materials = Counter()
    tiers = Counter()
    license_tiers = Counter()
    confidence = Counter()
    genres = Counter()
    themes = Counter()
    studios = Counter()
    splits = Counter()
    missing: dict[str, int] = {}
    mean_scores: list[float] = []
    popularity: list[float] = []
    favourites: list[float] = []
    episodes_n: list[float] = []
    duration: list[float] = []
    title_len: list[int] = []

    def miss(key: str) -> None:
        missing[key] = missing.get(key, 0) + 1

    for a in anime:
        year = a.get("year")
        if isinstance(year, int):
            years[year] += 1
        for f in ("title_canonical", "title_english", "title_japanese",
                  "year", "mean_score", "type", "status", "episodes", "duration_min",
                  "genres", "studios", "sources", "split", "quality_tier", "confidence"):
            if not a.get(f):
                miss(f)
        if isinstance(a.get("type"), str):
            types[a["type"]] += 1
        if isinstance(a.get("status"), str):
            statuses[a["status"]] += 1
        if isinstance(a.get("season"), str):
            seasons[a["season"]] += 1
        if isinstance(a.get("source_material"), str):
            materials[a["source_material"]] += 1
        if isinstance(a.get("quality_tier"), str):
            tiers[a["quality_tier"]] += 1
        if isinstance(a.get("license_tier"), str):
            license_tiers[a["license_tier"]] += 1
        if isinstance(a.get("confidence"), str):
            confidence[a["confidence"]] += 1
        if isinstance(a.get("split"), str):
            splits[a["split"]] += 1
        for g in (a.get("genres") or []):
            genres[str(g)] += 1
        for t in (a.get("themes") or []):
            themes[str(t)] += 1
        studio_list = a.get("studios")
        if isinstance(studio_list, list):
            for s in studio_list:
                studios[str(s)] += 1
        elif studio_list:
            studios[str(studio_list)] += 1
        for f in ("mean_score", "popularity", "favourites", "episodes", "duration_min"):
            v = num(a.get(f))
            if v is not None:
                {"mean_score": mean_scores, "popularity": popularity,
                 "favourites": favourites, "episodes": episodes_n,
                 "duration_min": duration}[f].append(max(v, 0.0))
        title_len.append(len(a.get("title_canonical", "")))

    profile["anime"] = {
        "count": len(anime),
        "splits": dict(splits),
        "years": {"min": min(years) if years else None,
                  "max": max(years) if years else None,
                  "total_distinct": len(years),
                  "top_years": top(years, 15)},
        "types": top(types, 20),
        "statuses": top(statuses, 15),
        "seasons": top(seasons, 6),
        "source_materials": top(materials, 15),
        "quality_tiers": dict(tiers),
        "license_tiers": dict(license_tiers),
        "confidence": dict(confidence),
        "mean_score": q(mean_scores),
        "popularity": q(popularity),
        "favourites": q(favourites),
        "episodes": q(episodes_n),
        "duration_min": q(duration),
        "title_len_chars": q(title_len),
        "episodes_coverage_pct": round(100.0 * (1 - missing.get("episodes", 0) / max(len(anime), 1)), 2),
        "mean_score_coverage_pct": round(100.0 * (1 - missing.get("mean_score", 0) / max(len(anime), 1)), 2),
        "missing_field_counts": {k: v for k, v in sorted(missing.items())},
        "genres": top(genres, 30),
        "themes": top(themes, 30),
        "studios": top(studios, 25),
        "genres_per_anime_mean": round(sum(genres.values()) / max(len(anime), 1), 3),
    }

    qa = load_lines("qa")
    qa_types: list[str] = []
    ql, al = [], []
    if qa:
        qt = qa[0].get("qtype")
        qa_is_list = isinstance(qt, list)
    for r in qa:
        if qa_is_list:
            qa_types.extend(str(x) for x in (r.get("qtype") or []))
        elif isinstance(r.get("qtype"), (str, int)):
            qa_types.append(str(r["qtype"]))
        ql.append(len(str(r.get("question", ""))))
        al.append(len(str(r.get("answer", ""))))
    profile["qa"] = {
        "count": len(qa),
        "question_len_chars": q(ql),
        "answer_len_chars": q(al),
        "types": top(Counter(qa_types), 25),
        "contains_grounded_fields_pct": round(100.0 * sum(1 for r in qa if r.get("grounded_fields")) / max(len(qa), 1), 2),
    }

    instructions = load_lines("instructions")
    il, iin, out = [], [], []
    itype = Counter()
    purpose = Counter()
    for r in instructions:
        itype[str(r.get("itype", "unknown"))] += 1
        purpose[str(r.get("purpose", "unknown"))] += 1
        il.append(len(str(r.get("instruction", ""))))
        iin.append(len(str(r.get("input", ""))))
        out.append(len(str(r.get("output", ""))))
    profile["instructions"] = {
        "count": len(instructions),
        "itypes": top(itype, 25),
        "purposes": top(purpose, 25),
        "instruction_len_chars": q(il),
        "input_len_chars": q(iin),
        "output_len_chars": q(out),
        "validated_pct": round(100.0 * sum(1 for r in instructions if r.get("validation")) / max(len(instructions), 1), 2),
    }

    rag = load_lines("rag_chunks")
    rl = []
    rk = Counter()
    for r in rag:
        rl.append(len(str(r.get("text", ""))))
        rk[str(r.get("kind", "unknown"))] += 1
    profile["rag"] = {
        "count": len(rag),
        "chunk_len_chars": q(rl),
        "kinds": top(rk, 20),
        "with_source_refs_pct": round(
            100.0 * sum(1 for r in rag if r.get("source_refs")) / max(len(rag), 1), 2),
    }

    desc = load_lines("descriptions")
    dk = Counter()
    dl = []
    for r in desc:
        dk[str(r.get("kind", "unknown"))] += 1
        dl.append(len(str(r.get("text", ""))))
    profile["descriptions"] = {"count": len(desc), "kinds": top(dk, 20), "text_len_chars": q(dl)}

    chars = load_lines("characters")
    roles = Counter()
    cdesc: list[int] = []
    cl = []
    for r in chars:
        roles[str(r.get("role", "unknown"))] += 1
        if isinstance(r.get("description"), str) and r["description"].strip():
            cdesc.append(len(r["description"].strip()))
        cl.append(len(str(r.get("name", ""))))
    profile["characters"] = {"count": len(chars), "roles": top(roles, 15), "description_len_chars": q(cdesc), "name_len_chars": q(cl)}

    eps = load_lines("episodes")
    elen: list[float] = []
    for r in eps:
        v = num(r.get("length_min"))
        if v is not None:
            elen.append(max(v, 0.0))
    profile["episodes"] = {"count": len(eps), "length_min": q(elen)}

    alt = load_lines("alt_titles")
    ak = Counter()
    alang = Counter()
    for r in alt:
        ak[str(r.get("kind", "unknown"))] += 1
        if r.get("lang"):
            alang[str(r["lang"])] += 1
    profile["alt_titles"] = {"count": len(alt), "kinds": top(ak, 15), "langs": top(alang, 15)}

    rel = load_lines("relationships")
    rk = Counter()
    for r in rel:
        rk[str(r.get("relation", "unknown"))] += 1
    profile["relationships"] = {"count": len(rel), "relations": top(rk, 20)}

    eul = load_lines("entity_links")
    euk = Counter()
    for r in eul:
        euk[str(r.get("link_method", "unknown"))] += 1
    profile["entity_links"] = {"count": len(eul), "link_methods": top(euk, 10)}

    prov = load_lines("provenance")
    pk = Counter()
    for r in prov:
        pk[str(r.get("source", "unknown"))] += 1
    profile["provenance"] = {"count": len(prov), "sources": top(pk, 10), "with_license_note_pct": round(100.0 * sum(1 for r in prov if r.get("license_note")) / max(len(prov), 1), 2)}

    studios_total = load_lines("studio") or load_lines("studios")
    if studios_total:
        profile["studios"] = {"count": len(studios_total)}

    files = {}
    for f in sorted(os.listdir(EXPORTS)):
        p = os.path.join(EXPORTS, f)
        if os.path.isfile(p):
            files[f] = os.path.getsize(p)
    profile["exports"] = {"file_count": len(files), "bytes_total": sum(files.values()), "files": files}

    genre_rows = load_lines("genres")
    theme_rows = load_lines("themes")
    profile["catalog"] = {"genres": len(genre_rows), "themes": len(theme_rows)}

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, ensure_ascii=False, indent=2)
    print(f"wrote {args.out} ({os.path.getsize(args.out)} bytes)")


if __name__ == "__main__":
    main()