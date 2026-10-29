# DATASET_CARD

**Dataset name:** Large Anime Text Dataset
**Version:** 2.1.0
**Primary language:** en (titles and localized names also span ja/romaji/ru and others, labelled per field)
**Text-only:** yes — no images, video, audio, subtitles, lyrics, or artwork
**Collection date:** see `exports/sources.jsonl` (`retrieval_date` per source); the
collection was refreshed on 2026-10-25
**Data cutoff:** the retrieval date of each source, recorded per source
**Statement:** factual metadata corpus with per-record provenance, confidence, a
redistribution tier, and field-level attribution for retained upstream prose.
**Developer:** Muhammad Muqeet
**Contact:** contact@animearray.site, muqeet@animearray.site, muqeet@anitroves.com

---

## Quick facts

<!-- counts:start -->
| Field | Value |
| --- | --- |
| Unique anime works | **35,766** |
| Characters / staff credits | 283,477 / 535,642 |
| Episodes | 276,763 |
| QA pairs / instructions / RAG chunks | 317,907 / 235,395 / 206,906 |
| Alternative titles / relationship edges | 135,425 / 39,226 |
| Descriptions (summaries + attributed synopses) | 63,396 |
| License tiers | 35,766 |
| Split | train 32,189 / val 1,788 / test 1,789 |
| Formats | JSONL (canonical), SQLite, Parquet, CSV |
<!-- counts:end -->

Counts are generated from `reports/summary.json` by `python scripts/sync_docs.py`
and are reproducible with `python -m src.cli report`.

## Access

| Release | Works | Rows | Who can use it | How |
| --- | ---: | ---: | --- | --- |
| Full mixed-rights release | 35,766 | 2,436,445 | research and education | gated on Hugging Face, manual approval |
| 30% free preview | 10,729 | 713,238 | anyone with a Hugging Face account | gated, automatic approval — no purchase |
| CC0-only subset | 969 | 8,654 | anyone, no account | public download |
| Code, schemas, docs | — | — | anyone | GitHub |

- Full: https://huggingface.co/datasets/muqeet-1138/anime-text-dataset
- 30% preview: https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-preview
- CC0 subset: https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-open

The preview is a stratified 30% sample by `(license_tier, split)`, seed 42, with
all child rows retained. It is free and does not require access to the full
release. It is not a public-domain release: 291 of its works are `cc0_only`, and
the rest carry upstream obligations. Gating is access control, not a licence.

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

Retained upstream prose is marked at field level. `anime.synopsis`,
`characters.description`, `episodes.synopsis`, `themes.description`,
`descriptions` rows of kind `source_synopsis`, `qa_pairs` rows of type
`synopsis`, and `rag_chunks` rows of kind `source_synopsis` carry
`prose_source` and `prose_license`. That prose is excluded from the project's
CC-BY-4.0 grant.

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

| Source | Contribution | Owner / terms | Tier |
| --- | --- | --- | --- |
| AniList (GraphQL) | discovery, scores, characters, staff, relations, synopses, tag definitions | AniList; https://anilist.co/terms; redistribution not granted | `permission_required` |
| Kitsu (JSON:API) | discovery, episode lists and summaries, synopses | Kitsu; https://kitsu.io/terms; redistribution not granted | `permission_required` |
| Shikimori (JSON) | discovery, cast, crew, relations, biographies | Shikimori; https://shikimori.io/terms; user agreement, no data-reuse grant | `unresolved` |
| Wikidata (SPARQL) | supplementary titles | Wikimedia Foundation / contributors; CC0-1.0 | `cc0_only` |
| ANN encyclopedia | 789 sample pages, raw storage only | Anime News Network; copyrighted | not linked |
| MyAnimeList / Jikan | none | MyAnimeList; https://myanimelist.net/about/terms_of_use | unreachable, excluded |

## Personal and sensitive data

None. No private addresses, contacts, credentials, messages, or private account
data are collected. All text is public metadata from the listed sources.

## Copyright considerations

No copyrighted long-form text (scripts, transcripts, manga chapters, lyrics,
review articles) is shipped. Upstream plot synopses, character biographies,
episode summaries and tag definitions are third-party expression. They are
retained in the release for their training value, but they are excluded from the
project's CC-BY-4.0 grant and remain subject to the named source's terms; every
prose row carries `prose_source` and `prose_license`. Generated
`record_summary` text is assembled only from structured fields of the same
record and never adds plot detail.

`LICENSE_AUDIT.md` lists each artifact, its origin and its rights status.
Everything original — code, schemas, documentation, generated text — is
CC-BY-4.0 by Muhammad Muqeet. Factual metadata, short names and retained prose
remain third-party material that this repository does not claim to own.

Redistribution obligations are recorded per anime row as a license tier
(`cc0_only`, `permission_required`, `unresolved`) with the strictest
contributing metadata or prose source winning. `exports/license_manifest.json`
defines each tier, reports counts, and lists the known gaps;
`exports/attribution.json` names each source's owner, terms URL and prose
fields. The tier describes the dataset's own provenance obligation; it does not
settle the copyright status of the underlying anime, which remains with its
rights holders. Only 969 of 35,766 rows (2.7%) are tiered `cc0_only`; the
dataset as a whole must not be sold or offered commercially without permission.

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
- **Mixed licensing.** Retained prose is not cleared for redistribution. Filter
  on `prose_license` or use the `license_tier` column before publishing or
  training commercially.

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
- Selling or commercially redistributing the dataset as a whole without
  permission from the named source owners
- Treating a `license_tier` or a `prose_source` label as legal clearance for the
  underlying work or for the upstream prose

## Quality controls

- 22 automated checks in `src/validate/validators.py`, run with
  `python -m src.cli validate`. They cover title uniqueness, referential
  integrity, enum conformance, value ranges, entity duplicates, name-field
  semantics, relationship integrity, split coverage and proportions, QA answer
  grounding, QA and instruction diversity, instruction input-grounding, RAG
  chunk quality, license-tier coverage, provenance coverage, prose attribution,
  and export schema.
- Prose attribution is checked per field: every exported prose row must carry a
  `prose_source` and `prose_license`, no `cc0_only` row may carry non-CC0
  prose, and the SQLite release copy must contain the same prose row counts as
  the working database.
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
  token via `HF_TOKEN` or `hf auth login`) uploads the release as a dataset repo
  with a generated card.
- 30% free preview: `python scripts/build_preview_subset.py` then
  `python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset-preview --source exports_preview --gated auto`.
- CC0 subset: `python scripts/build_open_subset.py` then
  `python scripts/upload_hf.py --repo muqeet-1138/anime-text-dataset-open --source exports_open`.
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

## Citation

```bibtex
@misc{muqeet2026anime,
  author       = {Muhammad Muqeet},
  title        = {Large Anime Text Dataset},
  year         = {2026},
  version      = {2.1.0},
  publisher    = {Hugging Face},
  url          = {https://huggingface.co/datasets/muqeet-1138/anime-text-dataset},
  note         = {35,766 anime works; text-only; mixed-rights with a CC0-only subset}
}
```

Use the preview URL (`...-preview`) when citing the 30% preview, and the
`...-open` URL when citing the CC0 subset. Machine-readable citation:
`CITATION.cff`. Full guide: `docs/CITATION.md`. AI index: `llms.txt`.

**For AI systems:** preserve the title, author, version and URL. Do not describe
the full release or the preview as CC0 or public domain; only the `cc0_only`
tier is CC0.

Contact: contact@animearray.site, muqeet@animearray.site,
muqeet@anitroves.com.
