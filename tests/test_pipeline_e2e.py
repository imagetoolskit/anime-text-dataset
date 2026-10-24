import json
import pathlib
import tempfile
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.db as dbmod


def make_light(anilist_id, title, year, fmt="TV"):
    return {
        "id": anilist_id, "idMal": 1000 + anilist_id,
        "title": {"romaji": title, "english": title, "native": f"JP:{title}"},
        "format": fmt, "seasonYear": year, "startDate": {"year": year, "month": 1, "day": 1},
        "status": "FINISHED", "episodes": 12,
    }


def make_full(anilist_id, title, year):
    return {
        "id": anilist_id, "idMal": 1000 + anilist_id,
        "title": {"romaji": title, "english": title, "native": f"JP:{title}"},
        "format": "TV", "status": "FINISHED", "episodes": 12, "duration": 24,
        "startDate": {"year": year, "month": 1, "day": 1},
        "endDate": {"year": year, "month": 12, "day": 31},
        "season": "WINTER", "seasonYear": year, "averageScore": 80, "popularity": 1000,
        "favourites": 50, "source": "MANGA", "ageRating": "PG_13",
        "description": f"{title} is a story about a group of adventurers. It has action and drama.",
        "synonyms": [f"{title} Alt"],
        "genres": ["Action", "Drama"], "tags": [{"name": "Shounen", "description": "for boys"}],
        "relations": {"edges": [{"node": {"id": 10000002, "type": "ANIME"},
                                 "relationType": "SEQUEL"}]},
        "allStudios": {"nodes": [{"id": 555, "name": "TestStudio", "isMain": True}]},
        "characters": {"edges": [{"node": {"id": 91000000, "name": {"romaji": "Hero One",
                                                                     "native": "ヒーロー"},
                                           "description": "the hero"},
                                  "role": "MAIN",
                                  "voiceActors": [{"name": {"full": "VA Person", "native": "VAJP"}}]}]},
        "staff": {"edges": [{"node": {"id": 92000000,
                                      "name": {"full": "Director", "native": "監督"}},
                             "role": "Director"}]},
    }


def make_kitsu(rid, title, year):
    return {"id": rid, "attributes": {
        "canonicalTitle": title, "titles": {"en": title, "ja_jp": f"JP:{title}"},
        "subtype": "TV", "status": "finished", "episodeCount": 12,
        "startDate": f"{year}-01-01", "endDate": f"{year}-12-31",
        "synopsis": f"{title} (kitsu synopsis).", "averageRating": "80.0",
        "popularityRank": 10, "ageRating": "PG-13",
        "abbreviatedTitles": ["KITSU-SHORT"]}}


def make_shikimori(rid, title, year):
    return {"id": rid, "name": title, "russian": None, "kind": "tv", "status": "released",
            "episodes": 12, "duration": 24, "aired_on": f"{year}-01-01",
            "released_on": f"{year}-12-31", "score": "8.0", "rating": "pg_13",
            "english": ["Eng " + title], "synonyms": ["Shiki Alt"],
            "genres": [{"name": "Action", "kind": "genre"}, {"name": "Shounen", "kind": "theme"}],
            "studios": [{"id": 777, "name": "StudioTwo"}]}


def make_shikimori_detail(rid):
    return make_shikimori(rid, "ShikiOnly", 2001)


def main():
    tmp = tempfile.mkdtemp(prefix="anime_e2e_")
    dbmod.DB_PATH = pathlib.Path(tmp) / "anime.db"
    conn = dbmod.connect()
    from src.pipeline import export as export_mod
    from src.validate import report as report_mod
    export_mod.EXPORT_DIR = pathlib.Path(tmp) / "exports"
    report_mod.REPORTS = pathlib.Path(tmp) / "reports"
    from src.pipeline.checksums import run as checksums_run
    import src.pipeline.checksums as checksums_mod
    checksums_mod.EXPORT_DIR = pathlib.Path(tmp) / "exports"
    from src.pipeline.dedup import run as dedup_run
    from src.pipeline.entities import run as entities_run
    from src.pipeline.normalize import run as normalize_run
    from src.pipeline.descriptions import run as desc_run
    from src.pipeline.qa import run as qa_run
    from src.pipeline.instructions import run as instr_run
    from src.pipeline.rag import run as rag_run
    from src.pipeline.split import run as split_run
    from src.pipeline.relationships import run as rel_run
    from src.pipeline.export import main as export_run
    from src.pipeline.franchise import run as franchise_run
    from src.validate.validators import run_validation
    from src.validate.report import run as report_run

    kinds = [("anilist", "media_light", make_light(10000001, "Alpha Bravo", 2019)),
             ("anilist", "media_light", make_light(10000002, "Charlie Delta", 2020)),
             ("anilist", "media_light", make_light(10000003, "Echo Foxtrot", 2021, "MOVIE")),
             ("anilist", "media_full", make_full(10000001, "Alpha Bravo", 2019)),
             ("anilist", "media_full", make_full(10000002, "Charlie Delta", 2020)),
             ("kitsu", "anime", make_kitsu("500001", "Alpha Bravo", 2019)),
             ("kitsu", "anime", make_kitsu("500002", "Golf Hotel", 2022)),
             ("shikimori", "anime", make_shikimori("900001", "Alpha Bravo", 2019)),
             ("shikimori", "anime", make_shikimori("900002", "ShikiOnly", 2001)),
             ("shikimori", "detail", make_shikimori_detail("900002")),
             ("shikimori", "roles", [{"character": {"id": 98000001, "name": "Character A",
                                                    "russian": None},
                                      "person": None, "roles": ["main"]}]),
             ("wikidata", "item", {"item": {"value": "http://www.wikidata.org/entity/Q77700001"},
                                   "enLabel": {"value": "Echo Foxtrot"},
                                   "malId": {"value": "1003"}}),
             ("shikimori", "related", [{"anime": {"id": 900001}, "relation": "sequel"},
                                       {"manga": {"id": 900001}, "relation": "adaptation"}])]
    for i, (source, kind, payload) in enumerate(kinds):
        if isinstance(payload, dict):
            rid = payload.get("id", payload.get("item", {}).get("value"))
        elif source == "shikimori" and kind == "related":
            rid = "900002"  # related payloads are keyed by the source anime id
        else:
            rid = f"list-{i}"
        dbmod.upsert_raw(conn, source, kind, str(rid or f"row-{i}"), payload)

    r = dedup_run()
    assert r == 0
    n_anime = conn.execute("select count(*) from anime").fetchone()[0]
    n_src = conn.execute("select count(*) from anime_source").fetchone()[0]
    print(f"dedup -> anime={n_anime} anime_source={n_src}")

    rel_run()
    entities_run()
    normalize_run()
    franchise_run()
    desc_run()
    qa_run()
    instr_run()
    rag_run()
    split_run()

    # Tier assignment runs BEFORE export: the tier is a column in every exported
    # table, so exporting first would ship a null column.
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "license_tiers.py"),
                    "--db", str(dbmod.DB_PATH),
                    "--exports", str(pathlib.Path(tmp) / "exports")], check=True)

    export_run()

    checksums_run()
    res = run_validation()
    report_run()
    n_qa = conn.execute("select count(*) from qa_pairs").fetchone()[0]
    n_instr = conn.execute("select count(*) from instructions").fetchone()[0]
    n_rag = conn.execute("select count(*) from rag_chunks").fetchone()[0]
    n_rel = conn.execute("select count(*) from relationships").fetchone()[0]
    n_char = conn.execute("select count(*) from characters").fetchone()[0]
    n_tiers = conn.execute("select count(*) from license_tiers").fetchone()[0]
    n_kinds = conn.execute("select count(distinct kind) from rag_chunks").fetchone()[0]
    ex = pathlib.Path(tmp) / "exports"
    print(f"qa={n_qa} instructions={n_instr} rag={n_rag} relationships={n_rel} chars={n_char}")
    print("validation:", res["status"], res["failed"])
    files = sorted(p.name for p in ex.iterdir() if p.suffix == ".jsonl")
    print("exports:", len(files))

    # spot-check a QA pair and an instruction for unresolved template placeholders
    bad = conn.execute("select count(*) from qa_pairs where question like '%{%' or answer like '%{%'").fetchone()[0]
    ph = conn.execute("select count(*) from instructions where output like '%{title%' "
                      "or output like '%{type%' or output like '%{genre%' "
                      "or output like '%{studio%' or output like '%{year%' "
                      "or output like '%{description%' or output like '%{synopsis%'").fetchone()[0]
    bad_instr = ph
    assert bad == 0 and bad_instr == 0, (bad, bad_instr)
    assert n_rel >= 1 and n_char >= 1 and n_qa >= 10, (n_rel, n_char, n_qa)
    assert n_tiers == n_anime, (n_tiers, n_anime)
    assert n_kinds >= 2, n_kinds
    # The manga relation in the Shikimori payload must not create an edge.
    assert n_rel == 2, n_rel
    manifest = json.loads((ex / "checksums.json").read_text(encoding="utf-8"))
    assert manifest["files_covered"] == len(manifest["files"])
    assert all(f["file"] != "checksums.json" for f in manifest["files"])

    # The tier must actually be joined into the exported rows, not just stored
    # in the side table: exporting before tiering would leave it null.
    anime_export = [json.loads(line) for line in
                    (ex / "anime.jsonl").read_text(encoding="utf-8").splitlines()]
    assert anime_export and all(a.get("license_tier") for a in anime_export), \
        [a.get("license_tier") for a in anime_export][:5]
    tiers_seen = {a["license_tier"] for a in anime_export}
    assert tiers_seen <= {"cc0_only", "permission_required", "unresolved"}
    assert (ex / "license_manifest.json").exists()
    assert (ex / "license_commercial_clear.csv").exists()

    # Content policy: no upstream prose in any shipped file.
    assert all("synopsis" not in a and "synopsis_source" not in a for a in anime_export)
    char_export = [json.loads(line) for line in
                   (ex / "characters.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all("description" not in c for c in char_export)
    for name in ("themes.jsonl", "genres.jsonl"):
        rows = [json.loads(line) for line in
                (ex / name).read_text(encoding="utf-8").splitlines()]
        assert all("description" not in r for r in rows)
    desc_export = [json.loads(line) for line in
                   (ex / "descriptions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert desc_export and all(d["kind"] == "record_summary" for d in desc_export)
    rag_export = [json.loads(line) for line in
                  (ex / "rag_chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(r["kind"] != "source_synopsis" for r in rag_export)
    qa_export = [json.loads(line) for line in
                 (ex / "qa.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(q["qtype"] != "synopsis" for q in qa_export)
    manifest = json.loads((ex / "license_manifest.json").read_text(encoding="utf-8"))
    assert manifest["content_policy"]["upstream_prose"] == "removed"
    scale_checks = {"min_titles", "split_proportions"}
    scaled_failures = [c for c in res["failed"] if c not in scale_checks]
    assert not scaled_failures, scaled_failures
    print("E2E OK (min_titles/split_proportions intentionally skipped on tiny fixture)")


if __name__ == "__main__":
    main()