# Schema — SQLite (rebuildable from exports/*.jsonl)

The shipped SQLite file (`exports/anime_dataset.sqlite`) is derived from the
canonical JSONL. Every per-anime table in it carries two derived columns —
`split` and `license_tier` — pre-joined from `splits` and `license_tiers`, so a
consumer can filter without a join.

The in-progress working database (`data/anime.db`) uses the same core tables
plus `raw_payload`, `checkpoint` and `run_log`.

## Core tables

- **anime** — one row per unique work. Columns: anime_id, title_canonical,
  title_english, title_japanese, synopsis, synopsis_source, type, status,
  episodes, duration_min, aired_from, aired_to, season, year, mean_score,
  popularity, favourites, source_material, age_rating, quality_tier, confidence.
  JSONL adds nested `alt_titles`, `genres`, `themes`, `studios`, `sources`,
  `franchise_id`, `license_tier`, `split`, and normalised `prose_source` /
  `prose_license` for the synopsis. The release SQLite copy carries those two
  attribution columns too.
- **anime_source** — entity-linking map (internal ↔ external). Columns: source,
  remote_id, anime_id, url, link_method, confidence. PK (source, remote_id);
  index on anime_id.
- **alt_titles** — anime_id, source, lang, kind, title, sources (JSON array of
  contributing sources); index on anime_id.
- **anime_genres / anime_themes** — (anime_id, genre|theme) primary key.
- **anime_studios** — anime_id, source, studio_name, source_studio_id, is_main;
  PK (anime_id, source, studio_name).
- **genres / themes / studios** — controlled vocabularies.
- **characters** — id, anime_id, source, remote_id, name, name_native, name_ru,
  role, description, voice_actors (JSON array), source_refs (JSON array of
  `{source, remote_id}`); UNIQUE(source, anime_id, remote_id). `description` is
  upstream biography text, retained with `prose_source` and `prose_license` in
  the release.
- **staff** — id, anime_id, source, remote_id, name, name_native, name_ru,
  roles (JSON array), source_refs (JSON array); UNIQUE(source, anime_id,
  remote_id).
- **episodes** — id, anime_id, source, remote_id, number, title, title_native,
  synopsis, aired, length_min; UNIQUE(source, anime_id, number). `synopsis` is
  upstream Kitsu prose, retained with `prose_source` and `prose_license`.
- **relationships** — anime_id, other_anime_id, other_source, other_remote_id,
  relation, source (a `+`-joined list when several sources agree); index on
  anime_id.
- **descriptions** — anime_id, kind (`record_summary` or `source_synopsis`),
  text, synthetic, provenance, source; PK (anime_id, kind).
- **qa_pairs** — id, anime_id, qtype, question, answer, template,
  grounded_fields (JSON array), prose_source; index on anime_id.
- **instructions** — id, anime_id, itype, instruction, input, output, synthetic,
  source_record_ids, purpose, validation; index on anime_id.
- **rag_chunks** — id, anime_id, chunk_index, kind, text, source_refs (JSON
  array), prose_source; index on anime_id.
- **franchises** — anime_id primary key, franchise_id; index on franchise_id.
- **license_tiers** — anime_id primary key, tier, sources (JSON array), reason.
- **dedup_log** — cluster_id, canonical_anime_id, method, members, created_at.
- **provenance** — entity, entity_id, source, url, retrieved_at, license_note,
  confidence; index on (entity, entity_id).
- **splits** — anime_id primary key, split.
- **quality_validation** — check_name, target, status, detail.

## Indexes in the exported SQLite

`anime(split)`, plus `anime_id` indexes on `anime`, `characters`, `staff`,
`episodes` and `relationships`. These are the access paths the training recipes
in `docs/TRAINING.md` rely on.

## Working-only tables (not part of the public export)

- **raw_payload** — source, remote_kind, remote_id, url, retrieved_at,
  http_status, license_note, payload; UNIQUE(source, remote_kind, remote_id).
  The raw collection cache; kept so collection can resume and be re-derived.
- **checkpoint** — key, value, updated_at. Collection/enrichment progress.
- **run_log** — ts, phase, message. Full operation history.

## Content policy in the release copy

Upstream prose is retained, not stripped. `exports/anime_dataset.sqlite` keeps
`anime.synopsis`, `characters.description`, `episodes.synopsis`,
`themes.description` and `descriptions.kind = 'source_synopsis'`, and adds
normalised `prose_source` / `prose_license` columns to every table that carries
prose. The JSONL files carry the same two columns.

The prose is excluded from the project's CC-BY-4.0 grant and remains subject to
the named source's terms. `exports/attribution.json` records each owner, terms
URL and redistribution status.

`python -m src.cli validate` enforces this: the `prose_attribution` check fails
if a prose row lacks a source or licence, if a `cc0_only` row carries non-CC0
prose, or if the SQLite copy is missing attribution. The `export_schema` check
fails if prose counts in the SQLite copy differ from the working database. See
`LICENSE_AUDIT.md` for the reasoning.
