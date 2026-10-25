# Data dictionary - Large Anime Text Dataset v2.1.0

All JSONL exports are UTF-8, one JSON object per line, stable IDs. `null` means
unavailable — never guessed. Language labels follow the source's own vocabulary
(`en`, `ja`, `romaji`, `native`, `ru`, …).

Every per-anime table also carries two derived columns in the JSONL, SQLite and
Parquet exports:

| Column | Meaning |
| --- | --- |
| `split` | `train` / `val` / `test`, assigned per anime with seed 42 |
| `license_tier` | `cc0_only` / `permission_required` / `unresolved` |

## Enumerations

| Field | Allowed values |
| --- | --- |
| `anime.type` | `TV`, `MOVIE`, `OVA`, `ONA`, `SPECIAL`, `TV_SPECIAL`, `SHORT`, `TV_SHORT`, `ONA_SHORT`, `MUSIC`, `PV`, `CM` |
| `anime.status` | `FINISHED`, `RELEASING`, `NOT_YET_RELEASED`, `CANCELLED`, `HIATUS` |
| `anime.season` | `WINTER`, `SPRING`, `SUMMER`, `FALL` |
| `anime.source_material` | `ORIGINAL`, `MANGA`, `LIGHT_NOVEL`, `NOVEL`, `WEB_NOVEL`, `WEB_MANGA`, `VISUAL_NOVEL`, `VIDEO_GAME`, `CARD_GAME`, `GAME`, `ANIME`, `MUSIC`, `BOOK`, `PICTURE_BOOK`, `RADIO`, `LIVE_ACTION`, `MIXED_MEDIA`, `DOUJINSHI`, `OTHER` |
| `anime.age_rating` | `G`, `PG`, `PG-13`, `R`, `R+`, `RX` |
| `characters.role` | `Main`, `Supporting`, `Background`, or `null` when the source does not state a role |
| `relationships.relation` | `SEQUEL`, `PREQUEL`, `PARENT_STORY`, `FULL_STORY`, `SIDE_STORY`, `SPIN_OFF`, `ALTERNATIVE`, `ALTERNATIVE_SETTING`, `ALTERNATIVE_VERSION`, `SUMMARY`, `ADAPTATION`, `CHARACTER`, `SAME_SERIES`, `SOURCE`, `COMPILATION`, `CONTAINS`, `OTHER` |

Values outside these sets are a validation failure (`enum_conformance`), so an
unmapped source value is nulled rather than passed through.

## anime.jsonl — one row per unique anime work

| Field | Type | Meaning | Origin |
| --- | --- | --- | --- |
| `anime_id` | integer | stable internal ID | assigned during dedup |
| `title_canonical` | string | preferred title | AniList romaji → Kitsu → Shikimori → Wikidata, whichever exists first |
| `title_english` | string | English title | per source |
| `title_japanese` | string | Japanese title | per source |
| `type` | enum | work format | normalized from source format/subtype/kind |
| `status` | enum | release status | normalized |
| `episodes` | integer | episode count | per source; `null` if unknown |
| `duration_min` | integer | per-episode minutes | AniList duration / Kitsu length |
| `aired_from`, `aired_to` | date | air/release window (`YYYY-MM-DD`) | normalized |
| `season` | enum | season bucket | AniList |
| `year` | integer | start year | source year, else recovered from `aired_from` |
| `mean_score` | real | score on a single 0–100 scale | AniList `averageScore`; Shikimori 0–10 scores rescaled ×10 |
| `popularity` | integer | popularity figure or rank | per source |
| `favourites` | integer | favourite count | AniList |
| `source_material` | enum | what the work adapts | normalized |
| `age_rating` | enum | content rating | normalized |
| `quality_tier` | string | `A` = multi-source, `B` = single source, `C` = sparse |
| `confidence` | string | `high`/`medium`/`low`, reflecting source agreement |
| `alt_titles` | array | all alternate titles | union of the `alt_titles` table |
| `genres` | array | genre names | `anime_genres` |
| `themes` | array | theme tags | `anime_themes` |
| `studios` | array | studio names | `anime_studios` |
| `sources` | array | `[{source, remote_id, url, link_method, confidence}]` | `anime_source` |
| `franchise_id` | integer | franchise cluster id | franchise stage |
| `license_tier` | enum | redistribution tier | strictest contributing source |
| `split` | enum | `train` / `val` / `test` | per-anime, seed 42 |

## characters.jsonl

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | integer | stable character record id |
| `anime_id` | integer | parent anime |
| `source` | string | `anilist` / `shikimori` |
| `remote_id` | string | source-side character id |
| `name` | string | romanized name |
| `name_native` | string | native-script name, or `null` |
| `name_ru` | string | Russian localized name, or `null` (Shikimori supplies these) |
| `role` | enum | `Main` / `Supporting` / `Background` / source label |
| `voice_actors` | array | `[{name}]` for the matched voice actors |
| `source_refs` | array | `[{source, remote_id}]` for every record merged into this row |

## staff.jsonl — one row per person per anime

`id`, `anime_id`, `source`, `remote_id`, `name`, `name_native`, `name_ru`,
`roles` (array of credit labels such as `Director`, `Music`, `Series
Composition`), `source_refs`.

Roles are kept in the source's own wording. Consumers that need a specific
credit should match on the role string and exclude the near-miss credit types —
`facts.find_staff` in the pipeline shows the pattern (`Director` excludes
`Episode Director`, `ADR Director`, `Assistant Director`, `Sound Director`).

## studios.jsonl

`studio_name` (primary key), `source_studio_id`, `url`.

## genres.jsonl / themes.jsonl

`genre` / `theme` (primary key). `themes.jsonl` also carries `description` and
`description_source`: the definition is upstream AniList tag prose, retained with
attribution and excluded from the project's CC-BY-4.0 grant.

## episodes.jsonl

`id`, `anime_id`, `source`, `remote_id`, `number`, `title`, `synopsis`, `aired`,
`length_min`, plus `prose_source` and `prose_license`. Unique on
`(source, anime_id, number)`. Episode summaries are upstream Kitsu prose and are
retained with attribution; `title_native` stays in the working database but is
not part of the release file.

Episode lists come from Kitsu. Works without a Kitsu match have an episode
count on `anime.jsonl` but no rows here.

## relationships.jsonl — directed edges between works

`anime_id`, `other_anime_id`, `other_source`, `other_remote_id`, `relation`,
`source`. `source` is a `+`-joined list when several sources contributed the
same edge.

Only anime-to-anime edges are stored. Shikimori returns manga relations in the
same payload and AniList relation nodes can be manga; those ids belong to a
different namespace and are rejected rather than matched against anime ids.

## alt_titles.jsonl

`anime_id`, `source`, `lang`, `kind` (`romaji`/`english`/`native`/`synonym`/…),
`title`, `sources` (array of every source that supplied this title). Rows are
deduplicated on a normalized title key per anime.

## descriptions.jsonl

| Field | Value |
| --- | --- |
| `kind` | `record_summary` or `source_synopsis` |
| `synthetic` | `1` for `record_summary`, `0` for `source_synopsis` |
| `provenance` | generation note, or the upstream-attribution note |
| `source` | registry id for `source_synopsis` rows |
| `prose_source`, `prose_license` | added on export for `source_synopsis` rows |

`record_summary` is assembled from structured fields of the same record — format,
year, episode count, studios, directors, source material, genres, themes, cast,
score — in one of several sentence orders. It contains no plot detail and is
covered by the project's CC-BY-4.0 grant.

`source_synopsis` is the upstream synopsis verbatim. It is third-party text,
excluded from the CC-BY-4.0 grant, and carries its source and licence status.
See `LICENSE_AUDIT.md`.

## qa.jsonl — grounded question/answer pairs

`id`, `anime_id`, `qtype`, `question`, `answer`, `template`, `grounded_fields`
(array of database fields the answer is computed from), `prose_source`,
`split`, `license_tier`.

Current question types: `type`, `air_date`, `episode_count`, `runtime`,
`studio`, `genres`, `themes`, `source`, `score`, `favourites`, `english_title`,
`japanese_title`, `alt_titles`, `characters`, `voice_actor`,
`character_role`, `director`, `composer`, `writer`, `episode_title`,
`relationship`, `relationship_reverse`, `franchise`, `multi_hop_studio`,
`multi_hop_episodes`, `comparison`, `synopsis`, `unknown_episodes`,
`unknown_studio`, `unknown_score`.

`synopsis` answers are the upstream synopsis, not a paraphrase. They carry
`prose_source` and `prose_license` and are excluded from the project's
CC-BY-4.0 grant.

`unknown_*` questions are deliberate abstentions: the answer states that the
field is not recorded for that work. They are capped at roughly one pair in
twenty so the corpus teaches calibration without being dominated by refusals.

Answers are emitted only when every value in them exists in the database for
that work. Validation re-reads each row's `grounded_fields` and confirms the
field is populated.

## instructions.jsonl — instruction-tuning examples

`id`, `anime_id`, `itype`, `instruction`, `input`, `output`, `synthetic`
(always `1`), `source_record_ids`, `purpose`, `validation`, `split`,
`license_tier`.

Instruction types: `metadata_extraction`, `record_summarization`,
`character_extraction`, `staff_credits`, `episode_list`, `relation_extraction`,
`franchise_grouping`, `title_normalization`, `entity_resolution`, `comparison`,
`json_repair`, `abstention`.

Every example is derivable from its own `input`: the source facts are rendered
into the input, and the task asks for a transformation of exactly those facts.
`validation` is set to `derivable_by_construction`, and
`instruction_input_grounding` re-checks a sample by confirming each output value
appears in the input.

## rag_chunks.jsonl

`id`, `anime_id`, `chunk_index`, `kind`, `text`, `source_refs`, `prose_source`,
`split`, `license_tier`.

`kind` is one of `record_summary`, `source_synopsis`, `title_aliases`,
`characters`, `voice_cast`, `staff`, `episodes`, `relations`. `source_refs` is an
array of `{source, remote_id, url?, fields}` naming the records and fields the
chunk was assembled from.

Most chunks are prose sentences assembled from factual fields, not JSON dumps.
`source_synopsis` chunks are the upstream synopsis verbatim; they carry
`prose_source` and `prose_license` and are excluded from the project's
CC-BY-4.0 grant. Every chunk ends in sentence punctuation so a retriever never
returns a fragment.

## entity_links.jsonl

`anime_id`, `source`, `remote_id`, `url`, `link_method`
(`mal_id`/`title_year`/`anilist_primary`/`kitsu_primary`/`shikimori_primary`/
`wikidata_primary`), `confidence`, `split`, `license_tier`.

## franchises.jsonl

`franchise_id`, `anime_id`, `split`, `license_tier`. Singleton clusters are
included, so this file has one row per anime.

Clusters are built only from relations that imply one continuous series:
`SEQUEL`, `PREQUEL`, `PARENT_STORY`, `FULL_STORY`, `SIDE_STORY`, `SPIN_OFF`,
`ALTERNATIVE_SETTING`, `ALTERNATIVE_VERSION`, `SUMMARY`. Sharing a source manga
(`ADAPTATION`) or a cameo (`CHARACTER`) does not merge works.

## license_tiers.jsonl

`anime_id`, `title`, `tier`, `sources`, `reason`.

Tier precedence is `unresolved` > `permission_required` > `cc0_only`; a work
takes the strictest tier among its contributing sources.
Definitions, counts, known gaps and a disclaimer live in
`exports/license_manifest.json`.

## dedup_merge_log.jsonl

`cluster_id`, `canonical_anime_id`, `method` (`mal_id`, `title_year`,
`normalized_title_year`), `members` (array), `created_at`.

## provenance.jsonl

`entity`, `entity_id`, `source`, `url`, `retrieved_at`, `license_note`,
`confidence`.

## sources.jsonl — source registry

`source_id`, `name`, `url`, `source_type`, `license`, `permission_status`,
`retrieval_method`, `retrieval_date`, `notes`.
