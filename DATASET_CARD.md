# DATASET_CARD

**Dataset name:** Large Anime Text Dataset
**Version:** 2.0.0
**Primary language:** en (titles and localized names also span ja/romaji/ru and others, labelled per field)
**Text-only:** yes — no images, video, audio, subtitles, lyrics, or artwork
**Collection date:** see `exports/sources.jsonl` (`retrieval_date` per source); the
collection was refreshed on 2026-10-25
**Data cutoff:** the retrieval date of each source, recorded per source
**Statement:** factual metadata corpus with per-record provenance, confidence and a
redistribution tier.
**Developer:** Muhammad Muqeet
**Contact:** muqeet@animearray.site, muqeet@anitroves.com

---

## Quick facts

<!-- counts:start -->
| Field | Value |
| --- | --- |
| Unique anime works | **35,766** |
| Characters / staff credits | 283,477 / 535,642 |
| Episodes | 276,763 |
| QA pairs / instructions / RAG chunks | 305,175 / 235,395 / 179,792 |
| Alternative titles / relationship edges | 135,425 / 39,226 |
| Descriptions | 35,766 |
| License tiers | 35,766 |
| Split | train 32,189 / val 1,788 / test 1,789 |
| Formats | JSONL (canonical), SQLite, Parquet, CSV |
<!-- counts:end -->

Counts are generated from `reports/summary.json` by `python scripts/sync_docs.py`
and are reproducible with `python -m src.cli report`.

## Motivation

Provide a large, text-only, provenance-tracked anime metadata corpus for LLM
fine-tuning, RAG evaluation, QA, entity linking, classification, and
recommendation — built entirely from public APIs with honest licensing and no
fabricated records. The dataset is organized so that every row carries the
provenance, confidence and license tier needed to filter it for a specific use,
including commercial training constraints.

## Composition

Per-anime tables (`anime`, `characters`, `staff`, `episodes`, `relationships`,
`descriptions`, `qa_pairs`, `instructions`, `rag_chunks`, `franchises`,
`alt_titles`) each carry `split` and `license_tier` columns in the SQLite and
Parquet exports, so a consumer can filter a training set without a join.

Reference tables (`genres`, `themes`, `studios`, `license_tiers`) and system
tables (`splits`, `dedup_log`, `provenance`, `quality_validation`, `checkpoint`,
`run_log`) ship in the SQLite export and as JSONL where listed in
`docs/DATA_DICTIONARY.md`.

## Data coverage

The dataset is the union of five public catalogues — **AniList, Kitsu,
Shikimori, Wikidata, and an ANN encyclopedia sample** — after entity resolution.
One work maps to one canonical `anime_id`; external source IDs are preserved per
record in `entity_links.jsonl`.

Coverage is **not** uniform across fields, and the release states the rate for
each one rather than an average:

- Identity fields (title, format, year) are near-complete.
- Cast, crew and episode records exist where the upstream source published them.
- Episode **lists** depend on a Kitsu match; works without one have an episode
  count but no per-episode rows.
- ANN contributes zero linked rows: it was sampled and retained in raw storage
  only.

Exact per-field rates are in `reports/final_report.md` under "Field coverage",
and machine-readable in `reports/summary.json` (`field_coverage`).

## Preprocessing

| Step | Detail |
| --- | --- |
| Text normalization | NFKC, zero-width and soft-hyphen removal, whitespace collapsed, HTML tags and entities stripped from locally stored upstream text before any fact is extracted |
| Enum canonicalization | `type`, `status`, `season`, `source_material`, `age_rating`, character role and relation names mapped onto closed vocabularies |
| Value repair | score `0` treated as missing; Shikimori's 0–10 scores rescaled to the 0–100 scale used by AniList; impossible years dropped or recovered from the air date; negative and out-of-range counts nulled |
| Duplicate works | merged on normalized title + year, with all child rows reassigned and the merge recorded in `dedup_log` |
| Duplicate entities | alt titles, characters, staff, episodes and relationship edges deduplicated on normalized keys; surviving rows keep a `source_refs` list of every contributing record |
| Name fields | `name_native` is native-script only; Cyrillic values that Shikimori stores there are moved to `name_ru` |
| Canonical identity | one `anime_id` per work; external links in `entity_links.jsonl` |
| Relation integrity | only anime-to-anime edges are kept; Shikimori manga ids and AniList manga nodes are rejected rather than matched against anime ids |
| Splits | 90/5/5, seed 42, assigned per anime (leakage-free) |
| Quality tiers | A = multi-source, B = single source, C = sparse |
| Confidence | `high`/`medium`/`low` per link and per work |

## Sources of data

| Source | Contribution | Terms | Tier |
| --- | --- | --- | --- |
| AniList (GraphQL) | discovery, scores, characters, staff, relations | public API; redistribution not granted | `permission_required` |
| Kitsu (JSON:API) | discovery, episode lists | public API; redistribution not granted | `permission_required` |
| Shikimori (JSON) | discovery, cast, crew, relations | no licence located | `unresolved` |
| Wikidata (SPARQL) | supplementary titles | CC0-1.0 | `cc0_only` |
| ANN encyclopedia | 789 sample pages, raw storage only | copyrighted | not linked |
| MyAnimeList / Jikan | none | — | unreachable, excluded |

## Personal and sensitive data

None. No private addresses, contacts, credentials, messages, or private account
data are collected. All text is public metadata from the listed sources.

## Copyright considerations

No copyrighted long-form text (scripts, transcripts, manga chapters, lyrics,
review articles) is shipped. Upstream plot synopses, character biographies and
episode summaries are third-party expression, so they are removed from every
export instead of paraphrased; the local working database retains them and is
not distributed. Generated `record_summary` text is assembled only from
structured fields of the same record and never adds plot detail.

`LICENSE_AUDIT.md` lists each artifact, its origin and its rights status.
Everything original — code, schemas, documentation, generated text — is
CC-BY-4.0 by Muhammad Muqeet. Factual metadata and short names remain
third-party material that this repository does not claim to own.

Redistribution obligations are recorded per anime row as a license tier
(`cc0_only`, `permission_required`, `unresolved`) with the strictest
contributing source winning. `exports/license_manifest.json` defines each tier,
reports counts, and lists the known gaps. The tier describes the dataset's own
provenance obligation; it does not settle the copyright status of the underlying
anime, which remains with its rights holders.

## Limitations and biases

- **Coverage bias:** union of the reachable public catalogues listed above;
  MyAnimeList is network-blocked and therefore absent.
- **Depth bias:** works that are popular on AniList and Shikimori carry richer
  cast, crew and relation data. Sparse or obscure works carry identity fields
  only. Per-field coverage is published instead of a single average.
- **Episode-list ceiling:** Kitsu is the only reachable per-episode source, so
  episode lists cannot exceed Kitsu coverage from this environment.
- **Recency/popularity bias** inherent to each source's catalogue.
- **Cross-language titles:** Japanese/romaji/English/Russian kept as labelled
  alternative titles; matching used normalized transliteration, which can
  over-merge titles that differ only by punctuation.
- **Voice-actor linkage completeness** varies by source.
- **Generated text is template-based.** QA pairs, instruction examples and RAG
  chunks are produced from structured fields. They are grounded and machine
  verifiable, but they are not human-authored and should not be treated as
  independent evidence about a work.

## Intended uses

- Instruction tuning for anime metadata QA and extraction (recipes in
  `docs/TRAINING.md`)
- RAG benchmarks and retrieval fine-tuning over `rag_chunks.jsonl`
- Entity-linking and recommendation research
- Multilingual title normalization evaluation
- Classification/ranking heads over `anime.jsonl`

## Out-of-scope uses

- High-stakes factual claims without cross-checking against live sources
- Recreating whole works from record summaries (not possible, not intended)
- Copyrighted-content generation or reproduction of scripts/transcripts
- Treating a `license_tier` as legal clearance for the underlying work

## Quality controls

- 21 automated checks in `src/validate/validators.py`, run with
  `python -m src.cli validate`. They cover title uniqueness, referential
  integrity, enum conformance, value ranges, entity duplicates, name-field
  semantics, relationship integrity, split coverage and proportions, QA answer
  grounding, QA and instruction diversity, instruction input-grounding, RAG
  chunk quality, license-tier coverage, provenance coverage, and export schema.
- Answer grounding is verified by re-reading each QA row's `grounded_fields`
  against the database, and instruction grounding by confirming every output
  value appears in that row's input.
- Quality tiers A/B/C and confidence high/medium/low per record.
- SHA-256 checksums for every export (`exports/checksums.json`, with `.sha256`
  sidecars). The manifest excludes itself so it can be verified.
- Full evidence in `reports/final_report.md`; machine-readable summary in
  `reports/summary.json`.

## Distribution tooling

- Statistical profile: `reports/data_profile.json` (regenerate with
  `python scripts/data_profile.py`); interactive view in
  `docs/explore.html`.
- Hugging Face publish: `scripts/upload_hf.py` (dry-run first,
  token via `HF_TOKEN`) uploads the release as a dataset repo with a
  generated card.
- EDA notebook: `examples/notebooks/EDA.ipynb`.
- License subsets: `python scripts/license_tiers.py` writes
  `exports/license_tier_<tier>.csv` and `exports/license_commercial_clear.csv`.
- Doc sync: `python scripts/sync_docs.py` refreshes the generated count tables;
  `--check` fails if they are stale.

## Maintenance and versioning

Versioned releases in `CHANGELOG.md`; historical releases are never silently
replaced. New collection runs produce a new snapshot with fresh retrieval
timestamps and checksums. Contributions follow `CONTRIBUTING.md`. See also
`docs/COMMANDS.md` for the exact terminal commands to reproduce any release.
