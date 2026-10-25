# License audit

This file is the artifact-by-artifact audit behind the repository's licensing
claim. It records what is original, what is third-party, which upstream prose is
retained, and what the maintainer does **not** claim. It is written to be
checkable against the tree, not to be taken on trust.

Audit owner: Muhammad Muqeet  
Contact: muqeet@animearray.site, muqeet@anitroves.com  
Last reviewed: 2026-10-25 (dataset version 2.1.0)

## The claim, stated precisely

> All original expression in this repository is authored by Muhammad Muqeet and
> licensed under Creative Commons Attribution 4.0 International (CC-BY-4.0).
> Upstream plot synopses, character biographies, episode summaries and tag
> definitions are retained in the release, excluded from that grant, and
> attributed to the source that published them. Attribution is not permission:
> those fields remain subject to the named source's terms.

The maintainer **does not** claim:

- copyright in upstream factual metadata, titles, names, prose, or the anime
  works themselves;
- that AniList, Kitsu, Shikimori or ANN content is sublicensed by this
  repository;
- that a CC-BY-4.0 grant over facts is possible or necessary — facts are not
  owned, but source terms may still contractually restrict bulk reuse;
- that any tier other than `cc0_only` is free of upstream obligations;
- that a `prose_source` label makes the text reusable. It makes the obligation
  visible and filterable.

The `LICENSE` file is this project's grant notice, not a copy of the Creative
Commons legal code; it points to the canonical CC-BY-4.0 text at
creativecommons.org. Python dependencies listed in `requirements.txt` and
`examples/training-requirements.txt` are installed by the user from their own
distributors and are not vendored or redistributed here.

## Why the prose is retained

Upstream synopses and biographies carry real training signal, so they are kept
rather than deleted or paraphrased. They are third-party expression; a close
paraphrase would still be a derivative work. Retaining them with a recorded
source and an explicit licence boundary is more honest than shipping a dataset
that looks cleaner than it is.

Retained prose and its measured coverage:

| Field / rows | Rows | Sources | Redistribution status |
| --- | ---: | --- | --- |
| `anime.synopsis` | 27,630 | Kitsu 20,715; AniList 5,157; Shikimori 1,758 | permission required / unresolved |
| `characters.description` | 84,329 | AniList 42,370; Shikimori 41,959 | permission required / unresolved |
| `episodes.synopsis` | 44,465 | Kitsu 44,465 | permission required |
| `themes.description` | 422 | AniList 422 | permission required |
| `descriptions.kind = 'source_synopsis'` | 27,630 | same as `anime.synopsis` | permission required / unresolved |
| `rag_chunks.kind = 'source_synopsis'` | 27,114 | same as `anime.synopsis` | permission required / unresolved |
| `qa_pairs.qtype = 'synopsis'` | 21,521 | Kitsu 16,028; AniList 4,086; Shikimori 1,407 | permission required / unresolved |
| `genres.description` | 0 | — | not populated |

Every prose row carries:

- `prose_source` — registry id (`anilist`, `kitsu`, `shikimori`, `unknown`);
- `prose_license` — `permission_required`, `unresolved`, or `allowed`.

All 27,630 synopses have a verified source label; there are zero unlabelled
synopses. The `unknown` bucket exists in `attribution.json` so a future
unlabelled row is visible rather than silently attributed.

## Source owners and terms

| Source | Owner | Terms | Redistribution |
| --- | --- | --- | --- |
| AniList | AniList | https://anilist.co/terms | permission required; no redistribution grant |
| Kitsu | Kitsu | https://kitsu.io/terms | permission required; no data-redistribution grant located |
| Shikimori | Shikimori | https://shikimori.io/terms | unresolved; general user agreement, no data-reuse grant |
| Wikidata | Wikimedia Foundation and Wikidata contributors | https://www.wikidata.org/wiki/Wikidata:Licensing | CC0-1.0 |
| Anime News Network | Anime News Network | no terms page located | unresolved; copyrighted |
| MyAnimeList / Jikan | MyAnimeList | https://myanimelist.net/about/terms_of_use | not collected |

Terms URLs were fetched on 2026-10-25. Shikimori's page resolves and is a 2012
general user agreement; it contains no data-reuse grant, so the status remains
`unresolved` rather than being read as permission.

## Artifact inventory

### Original work — CC-BY-4.0

| Artifact | Author | Basis |
| --- | --- | --- |
| `src/**` (pipeline, validators, CLI) | Muhammad Muqeet | original code |
| `scripts/**` (tiers, profile, doc sync) | Muhammad Muqeet | original code |
| `tests/**` | Muhammad Muqeet | original code |
| `tools/dev/**` | Muhammad Muqeet | unmaintained one-off diagnostics; not part of the pipeline |
| `.github/workflows/ci.yml`, `pytest.ini`, `requirements.txt` | Muhammad Muqeet | original CI/test configuration |
| `config/**` | Muhammad Muqeet | original configuration |
| `README.md`, `DATASET_CARD.md`, `docs/**`, `LICENSE_AUDIT.md`, `NOTICE`, `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `AUTHORS.md`, `CITATION.cff` | Muhammad Muqeet | original prose |
| `docs_src/*.html`, `docs/*.html`, `docs/*.css`, `docs/*.js` | Muhammad Muqeet | original code and design |
| `examples/**` | Muhammad Muqeet | original code |
| `reports/summary.json`, `reports/data_profile.json`, `reports/final_report.md` | Muhammad Muqeet | generated measurements |
| `exports/descriptions.jsonl` (`record_summary` rows) | Muhammad Muqeet | template-generated from facts |
| `exports/qa.jsonl` (non-synopsis rows) | Muhammad Muqeet | template-generated, grounded |
| `exports/instructions.jsonl` | Muhammad Muqeet | template-generated, grounded |
| `exports/rag_chunks.jsonl` (non-synopsis rows) | Muhammad Muqeet | assembled from factual fields |
| `exports/dedup_merge_log.jsonl` | Muhammad Muqeet | pipeline decisions |
| `exports/license_tiers.jsonl`, `exports/license_manifest.json`, `exports/license_tier_*.csv` | Muhammad Muqeet | classification of the above |
| `exports/attribution.json`, `exports/provenance.jsonl`, `exports/sources.jsonl` | Muhammad Muqeet | provenance records |

### Third-party prose — retained, attributed, excluded from CC-BY

| Artifact | Contains | Upstream status |
| --- | --- | --- |
| `exports/anime.jsonl`, `anime.csv`, `anime.parquet` | `synopsis`, `synopsis_source` | Kitsu / AniList / Shikimori prose; `prose_source` + `prose_license` |
| `exports/characters.jsonl` | `description` | AniList / Shikimori biography text; `prose_source` + `prose_license` |
| `exports/episodes.jsonl` | `synopsis` | Kitsu summaries; `prose_source` + `prose_license` |
| `exports/themes.jsonl` | `description` | AniList tag definitions; `prose_source` + `prose_license` |
| `exports/descriptions.jsonl` (`source_synopsis` rows) | verbatim upstream synopsis | source recorded in `prose_source` |
| `exports/rag_chunks.jsonl` (`source_synopsis` rows) | upstream synopsis chunk | source recorded in `prose_source` |
| `exports/qa.jsonl` (`synopsis` rows) | upstream-synopsis answer | source recorded in `prose_source` |

### Third-party facts and short names — not owned, attributed

| Artifact | Contains | Upstream status |
| --- | --- | --- |
| `exports/anime.jsonl`, `anime.csv`, `anime.parquet` | titles, format, dates, counts, scores, season, source material, studio/genre/theme links | mixed: Wikidata CC0; Kitsu and AniList terms do not grant redistribution; Shikimori unresolved |
| `exports/characters.jsonl`, `staff.jsonl` | character and credit names, roles, voice-actor names | same mixed status |
| `exports/episodes.jsonl` | episode numbers, titles, air dates, lengths | Kitsu API data, no redistribution grant |
| `exports/relationships.jsonl`, `franchises.jsonl` | relation type and linked titles | mixed; structural facts |
| `exports/alt_titles.jsonl`, `studios.jsonl`, `genres.jsonl` | names and labels | mixed; short names |
| `exports/entity_links.jsonl` | cross-source id links | pipeline-generated joins over facts |

Attribution for these is carried in `exports/attribution.json`,
`exports/sources.jsonl`, `exports/provenance.jsonl`, `NOTICE`,
`ACKNOWLEDGMENTS.md` and `docs/LICENSE_NOTES.md`, and each anime row carries a
`license_tier`.

### Not distributed

| Path | Why it is excluded |
| --- | --- |
| `data/anime.db`, `data/anime.db.bak` | working database, including `raw_payload` |
| `data/cache/**` | raw HTTP payload cache |
| `raw_payload` table (inside the DB) | verbatim upstream JSON |
| `logs/**` | run logs, may quote upstream errors |
| ANN sample pages | copyrighted encyclopedia pages, linked to zero exported rows |

`.gitignore` excludes `data/`, `exports/`, `logs/` and database files, so a
clone of the source repository does not contain them. Release archives are
built from `exports/` only, after `validate` has passed.

Analytics output in `reports/` and `docs/data/profile.json` is computed from the
release exports and therefore includes prose-derived lengths.

## How to verify this audit

```bash
python -m src.cli validate      # export_schema + prose_attribution gates
python -m src.cli report        # regenerates reports/summary.json
python scripts/sync_docs.py --check
```

`validate` fails if a prose field is missing from the export, if the SQLite
release copy carries fewer prose rows than the working database, if a prose row
lacks `prose_source` or `prose_license`, if a `cc0_only` row carries non-CC0
prose, or if `attribution.json` is missing a source.

Manual spot checks:

```bash
grep -c '"synopsis"' exports/anime.jsonl
grep -c '"prose_license"' exports/characters.jsonl
sqlite3 exports/anime_dataset.sqlite "select count(*) from anime where synopsis is not null;"
python -c "import json;print(len(json.load(open('exports/attribution.json'))['sources']))"
```

Expected: non-zero prose counts, one `prose_license` per prose row, and seven
registry entries (six sources plus `unknown`).

## Residual risk and open questions

1. **Database rights.** Factual compilations can attract sui generis database
   rights in some jurisdictions (notably the EU). CC-BY-4.0 over the project's
   selection and arrangement does not override an upstream database right.
2. **Contract terms.** AniList's API terms permit API use but do not grant
   redistribution of content, and prohibit hoarding or mass collection; Kitsu's
   terms likewise grant no redistribution of API data; Shikimori's user
   agreement grants no data-reuse right. Those rows remain tiered
   `permission_required` or `unresolved` in `license_manifest.json`; the tier is
   an obligation label, not a clearance.
3. **Commercial use.** Only 969 of 35,766 rows (2.7%) are tiered `cc0_only`.
   The dataset as a whole cannot be sold or offered commercially without
   permission from the named source owners.
4. **Names and marks.** Anime, character and studio names may be trademarks.
   They are used nominatively to identify the works; no endorsement is implied.
5. **No legal advice.** This audit is an engineering record, not a legal
   opinion. A distributor should confirm the intended use against each source's
   current terms.
6. **Removal on request.** If a rights holder objects to an included field or
   name, contact the maintainer and the row will be removed.
