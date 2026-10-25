# Changelog

All notable changes to this dataset project are recorded here. Large data
files ship as release assets, not through Git history.

## [2.0.0] — 2026-10-25

Correctness, consistency and licensing release. Every derived table was rebuilt
from a deeper enrichment pass; several data-integrity defects were fixed.

**Enrichment**

- Full AniList records raised from 12,721 to 22,257 works (the whole linked
  set; ~360 IDs are no longer served by the API).
- Shikimori detail, cast/crew and related endpoints re-collected for the depth
  tier; Kitsu episode lists re-collected.
- `entities` re-run over the expanded payloads, so AniList characters and staff
  now exist as rows for every work that has a full record.

**New: `normalize` phase**

- Merges exact duplicate works (same normalized title + year), reassigning every
  child row and logging the merge in `dedup_log`.
- Canonicalizes `type`, `status`, `season`, `source_material`, `age_rating`,
  character roles and relation names onto closed vocabularies.
- Repairs values: score `0` → missing, Shikimori 0–10 scores rescaled to 0–100,
  impossible years dropped, negative counts nulled, HTML stripped.
- Deduplicates alternative titles, characters, staff, episodes and relationship
  edges; surviving rows keep a `source_refs` list of the merged records.
- Moves Cyrillic names out of `name_native` into `name_ru`, and merges
  cross-source person rows.

**Data-integrity fixes**

- Relationship building matched Shikimori **manga** ids and AniList **manga**
  relation nodes against anime ids, creating false edges. Both paths now accept
  anime targets only.
- Franchise QA inverted its sibling lookup, so franchise questions could return
  unrelated works. Fixed in `facts.load_children`.
- `checksums.json` hashed itself and the `.sha256` sidecars, so a second run
  could never verify. The manifest now excludes itself and records
  `algorithm`, `files_covered` and `excluded`.
- Comparisons in the instruction set fell back to a random partner. They now use
  franchise siblings, else a same-format same-year peer, else nothing.

**Derived text rewritten**

- QA: ~30 question types (metadata, cast, crew, episodes, relations, reverse
  relations, franchise, multi-hop, comparison) with several phrasings each, plus
  deliberate abstentions at roughly one pair in twenty.
- Instructions: 12 task types, every one derivable from its own `input` field.
  The previous `json_repair`-style task that could not be derived from its input
  was removed.
- RAG: prose chunks instead of JSON dumps, each labelled with a `kind`
  (`record_summary`, `title_aliases`, `characters`, `voice_cast`, `staff`,
  `episodes`, `relations`) and real `source_refs`.
- Descriptions: `record_summary` replaces the old `original` kind and is built
  only from structured fields of the same record.

**Licensing**

- Tiers renamed to describe the obligation they impose: `cc0_only`,
  `permission_required`, `unresolved` (precedence, strictest wins). Kitsu is
  `permission_required`: no CC-BY-SA data grant exists, only API terms.
- `exports/license_manifest.json` gained tier definitions, counts, known gaps
  and an explicit statement that a tier is not legal clearance.
- Per-tier id lists plus `license_commercial_clear.csv` regenerated from the new
  tiers.
- **Upstream prose removed from every export.** `anime.synopsis`,
  `anime.synopsis_source`, `characters.description`, `episodes.synopsis`,
  `themes.description` and `genres.description` are dropped from JSONL/CSV/
  Parquet and nulled in the SQLite release copy; `source_synopsis` descriptions,
  RAG chunks and QA rows are no longer generated. Paraphrasing was rejected
  because it would still be a derivative work.
- New `LICENSE_AUDIT.md` lists every artifact, its origin and its rights status,
  and states what the maintainer does not claim.
- `export_schema` validation now fails on any reappearing prose field.
- `license_manifest.json` gained a `content_policy` block.

**Validation and reporting**

- 21 checks (up from 12), adding `qa_fields_resolve`, `instruction_diversity`,
  `rag_chunk_quality`, `license_coverage`, `provenance_coverage`,
  `export_schema` and `instruction_grounding`.
- `reports/final_report.md` is generated entirely from the database: field
  coverage per attribute, QA/instruction/description/RAG-kind distributions,
  license tiers, measured limitations, and the phase log.
- `scripts/sync_docs.py` regenerates the count tables in `README.md`,
  `DATASET_CARD.md`, `docs/TRAINING.md` and the `{{n:…}}` tokens in the HTML
  pages from `reports/summary.json`; `--check` fails when they are stale.
- Test suite expanded to unit tests plus an end-to-end fixture build, covering
  covering normalization, tier coverage, RAG kinds, relation filtering and the
  checksums manifest.

**Engineering**

- `examples/finetune_lora.py` now actually applies a `peft` `LoraConfig` and
  saves adapters; it previously full fine-tuned while claiming to be LoRA.
- Training docs use the current `trl` API (`processing_class`, a frozen
  reference model for DPO) and pin `trl>=0.16,<0.30`.
- CI pins actions to commit SHAs, adds a concurrency group, a job timeout and a
  `sync_docs --check` step so stale documentation fails the build.
- Site pages moved to `docs_src/` and rendered into `docs/`; tokens stay in the
  source, so the doc-sync check keeps working after the first render instead of
  freezing the numbers.
- The CLI answers `-h` / `--help`; one-off probe scripts moved out of `tests/`
  into `tools/dev/` with a warning README.
- `config/.env.example` is now true: `src/config.py` applies the documented
  `ATDS_*` environment overrides, loads `.env` from the repository root, and
  coerces values to the type of the setting they replace.

**Documentation**

- `README.md`, `DATASET_CARD.md`, `docs/DATA_DICTIONARY.md`, `docs/SCHEMAS.md`,
  `docs/LICENSE_NOTES.md`, `docs/COMMANDS.md` and `docs/TRAINING.md` rewritten
  against the actual schema and data. Numeric claims are machine-synced rather
  than typed.

## [1.1.0] — 2026-10-08

Substance upgrade and per-anime license tiering.

- Backfill phase (`backfill`) + live detail pass (`refill`): Shikimori detail
  for 8,822 works and full AniList records for all 12,721 depth-tier works.
- Coverage gains (35,767 works): synopsis 60% → 77%, age rating → 78%,
  genres-covered works 7.2k → 17.3k, studios-covered 7.1k → 14.0k,
  alternative titles 116k → 263k, staff rows 386k → 400k, RAG chunks 98k →
  106k.
- New `scripts/license_tiers.py` → `exports/license_tiers.jsonl` +
  `license_tier_<tier>.csv` (mechanical subset filters); dated per-source
  verdicts in `docs/LICENSE_NOTES.md`.
- Entities re-extracted from the expanded full payloads; downstream chain
  (descriptions/qa/instructions/franchise/rag/split/export) regenerated with
  new checksums; `reports/data_profile.json` synced to `docs/data/profile.json`.

## [1.0.0] — 2026-10-06

Initial release.

- Discovery across AniList (~22k), Kitsu (22,494), Shikimori (24,040),
  Wikidata (Q1107, 9,538 items), and an ANN ID sample (2,000).
- Pipeline: discover → dedup → enrich → entities → relationships →
  descriptions → qa → instructions → franchise → rag → split → validate →
  export → checksums → report.
- Primary export: JSONL; also SQLite, Parquet, CSV; SHA-256 checksums.
- Exact counts, validation results, and limitations in `reports/`.

_Notable constraint this release:_ MyAnimeList/Jikan was unreachable
(network-blocked) and is excluded; the unique-anime count reflects the union
of the reachable, permitted sources (see `reports/final_report.md`).

## [1.0.1] — 2026-10-07

Final run; dataset verified.

- Dedup normalization tightened (space/punctuation/underscore-insensitive) to
  match title-collision validation; Wikidata labels fall back to `itemLabel`.
- Validation passes: 35,767 unique anime with titles, no title+year
  collisions, no orphans, no split leakage, all QA grounded.
- Exports regenerated: 23 files + SHA-256 checksums (`exports/checksums.json`).
- `tests/test_smoke.py` updated to assert the corrected normalization.