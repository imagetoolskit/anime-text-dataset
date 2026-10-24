# License audit

This file is the artifact-by-artifact audit behind the repository's licensing
claim. It records what is original, what is third-party, what was removed, and
what the maintainer does **not** claim. It is written to be checkable against
the tree, not to be taken on trust.

Audit owner: Muhammad Muqeet  
Contact: muqeet@animearray.site, muqeet@anitroves.com  
Last reviewed: 2026-10-24 (dataset version 2.0.0)

## The claim, stated precisely

> All original expression in this repository is authored by Muhammad Muqeet and
> licensed under Creative Commons Attribution 4.0 International (CC-BY-4.0).
> Third-party plot synopses, character biographies and episode summaries are not
> included in any release artifact. What remains from upstream sources is
> factual metadata (titles, dates, counts, scores, credit names, genre labels)
> and short names, which the maintainer does not claim to own.

The maintainer **does not** claim:

- copyright in upstream factual metadata, titles, names, or the anime works
  themselves;
- that AniList, Shikimori or ANN content is sublicensed by this repository;
- that a CC-BY-4.0 grant over facts is possible or necessary — facts are not
  owned, but source terms may still contractually restrict bulk reuse;
- that any tier other than `cc0_only` is free of upstream obligations.

The `LICENSE` file is this project's grant notice, not a copy of the Creative
Commons legal code; it points to the canonical CC-BY-4.0 text at
creativecommons.org. Python dependencies listed in
`requirements.txt` and `examples/training-requirements.txt` are installed by the
user from their own distributors and are not vendored or redistributed here.

## Why the prose was removed, not rewritten

Plot synopses and character bios are creative expression. No source in this
pipeline grants redistribution, and a close paraphrase is still a derivative
work, so rewriting would not have made them the maintainer's to license.
Removal is the only option that supports an honest claim.

Removed from every export (JSONL, CSV, Parquet and the SQLite release copy):

| Field / rows | Origin | Action |
| --- | --- | --- |
| `anime.synopsis` | Kitsu / AniList / Shikimori prose | dropped from export |
| `anime.synopsis_source` | pipeline provenance for the above | dropped from export |
| `characters.description` | Shikimori / AniList biography text | dropped from export |
| `episodes.synopsis` | Kitsu episode summary | dropped from export |
| `themes.description` | AniList tag definitions | dropped from export |
| `genres.description` | label definitions | dropped from export |
| `descriptions.kind = 'source_synopsis'` | verbatim upstream synopsis | deleted |
| `rag_chunks.kind = 'source_synopsis'` | windowed upstream synopsis | not generated |
| `qa_pairs.qtype = 'synopsis'` | upstream-synopsis answer | not generated |

The columns still exist in the local working database so the collection step
can join and deduplicate safely. That database is not a release artifact.

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
| `exports/descriptions.jsonl` (`record_summary` only) | Muhammad Muqeet | template-generated from facts |
| `exports/qa.jsonl` | Muhammad Muqeet | template-generated, grounded |
| `exports/instructions.jsonl` | Muhammad Muqeet | template-generated, grounded |
| `exports/rag_chunks.jsonl` | Muhammad Muqeet | assembled from factual fields |
| `exports/dedup_merge_log.jsonl` | Muhammad Muqeet | pipeline decisions |
| `exports/license_tiers.jsonl`, `exports/license_manifest.json`, `exports/license_tier_*.csv` | Muhammad Muqeet | classification of the above |
| `exports/provenance.jsonl`, `exports/sources.jsonl` | Muhammad Muqeet | provenance records |

### Third-party facts and short names — not owned, attributed

| Artifact | Contains | Upstream status |
| --- | --- | --- |
| `exports/anime.jsonl`, `anime.csv`, `anime.parquet` | titles, format, dates, counts, scores, season, source material, studio/genre/theme links | mixed: Wikidata CC0; Kitsu and AniList terms do not grant redistribution; Shikimori unresolved |
| `exports/characters.jsonl`, `staff.jsonl` | character and credit names, roles, voice-actor names | same mixed status; no biography text |
| `exports/episodes.jsonl` | episode numbers, titles, air dates, lengths | Kitsu API data, no redistribution grant; no summaries |
| `exports/relationships.jsonl`, `franchises.jsonl` | relation type and linked titles | mixed; structural facts |
| `exports/alt_titles.jsonl`, `studios.jsonl`, `genres.jsonl`, `themes.jsonl` | names and labels | mixed; short names |
| `exports/entity_links.jsonl` | cross-source id links | pipeline-generated joins over facts |

Attribution for these is carried in `exports/sources.jsonl`,
`exports/provenance.jsonl`, `NOTICE`, `ACKNOWLEDGMENTS.md` and
`docs/LICENSE_NOTES.md`, and each anime row carries a `license_tier`.

### Not distributed

| Path | Why it is excluded |
| --- | --- |
| `data/anime.db`, `data/anime.db.bak` | working database; still holds upstream synopsis/bio columns |
| `data/cache/**` | raw HTTP payload cache |
| `raw_payload` table (inside the DB) | verbatim upstream JSON, including prose |
| `logs/**` | run logs, may quote upstream errors |
| ANN sample pages | copyrighted encyclopedia pages, linked to zero exported rows |

`.gitignore` excludes `data/`, `exports/`, `logs/` and database files, so a
clone of the source repository does not contain them. Release archives are
built from `exports/` only, after `validate` has passed.

Analytics output in `reports/` and `docs/data/profile.json` is computed from the
release exports, which contain no upstream prose.

## How to verify this audit

```bash
python -m src.cli validate      # runs export_schema incl. the content-policy gate
python -m src.cli report        # regenerates reports/summary.json
python scripts/sync_docs.py --check
```

`validate` fails if any export still carries a banned key
(`synopsis`, `synopsis_source`, `description`), if any non-`record_summary`
description survives, if any `source_synopsis` RAG chunk or `synopsis` QA row
survives, or if the SQLite release copy has a non-empty prose column.

Manual spot checks:

```bash
grep -c '"synopsis"' exports/*.jsonl
grep -c '"description"' exports/characters.jsonl
sqlite3 exports/anime_dataset.sqlite "select count(*) from anime where synopsis is not null;"
```

Expected result: zero matches, zero rows.

## Residual risk and open questions

1. **Database rights.** Factual compilations can attract sui generis database
   rights in some jurisdictions (notably the EU). CC-BY-4.0 over the project's
   selection and arrangement does not override an upstream database right.
2. **Contract terms.** AniList's API terms permit API use but do not grant
   redistribution of content, and prohibit hoarding or mass collection; Kitsu's
   terms likewise grant no redistribution of API data; Shikimori's terms could
   not be located. Those rows remain tiered `permission_required` or
   `unresolved` in `license_manifest.json`; the tier is an obligation label,
   not a clearance.
3. **Names and marks.** Anime, character and studio names may be trademarks.
   They are used nominatively to identify the works; no endorsement is implied.
4. **No legal advice.** This audit is an engineering record, not a legal
   opinion. A distributor should confirm the intended use against each source's
   current terms.
5. **Removal on request.** If a rights holder objects to an included fact or
   name, contact the maintainer and the row will be removed.
