# Anime Text Dataset — Final Report

Generated: 2026-10-25T18:24:44+00:00
Platform: Windows-10-10.0.19045-SP0 / Python 3.12.10
Seed: 42 | Max runtime: 12h

Every count below is read from the database at generation time. Nothing in this
report is estimated, projected, or carried over from an earlier run.

## Headline

- **Unique anime works with at least one title: 35,766**
- Minimum required (20,000): **MET**
- Target (50,000): **NOT MET**
- Characters: 283,477 | Staff credits: 535,642 | Episodes: 276,763
- QA pairs: 317,907 | Instructions: 235,395 | RAG chunks: 206,906
- Validation: all checks passed

## Field coverage

Share of the 35,766 anime rows that carry a value for each field.

| Field | Anime | Share |
| --- | ---: | ---: |
| type | 35,724 | 99.9% |
| status | 34,797 | 97.3% |
| year | 33,892 | 94.8% |
| aired_from | 33,692 | 94.2% |
| episodes (count) | 33,778 | 94.4% |
| duration_min | 31,520 | 88.1% |
| mean_score | 21,351 | 59.7% |
| popularity | 27,755 | 77.6% |
| favourites | 22,067 | 61.7% |
| source_material | 19,694 | 55.1% |
| title_english | 24,890 | 69.6% |
| title_japanese | 33,651 | 94.1% |
| studios | 22,688 | 63.4% |
| genres | 27,629 | 77.2% |
| themes | 17,464 | 48.8% |
| alt titles | 32,518 | 90.9% |
| characters | 17,939 | 50.2% |
| character roles | 17,939 | 50.2% |
| voice actors | 11,709 | 32.7% |
| staff credits | 23,285 | 65.1% |
| episode list | 21,604 | 60.4% |
| episode titles | 3,535 | 9.9% |
| relationships | 17,948 | 50.2% |

## Coverage by source (anime_source rows; one anime may map to several sources)

- shikimori: 24,009
- anilist: 22,617
- kitsu: 22,494
- wikidata: 8,561

### Link methods

- anilist_primary: 4,426
- kitsu_primary: 3,173
- mal_id: 51,969
- shikimori_primary: 7,034
- title_year: 10,082
- wikidata_primary: 997

## Raw payloads stored

- anilist:media_full: 22,257
- anilist:media_light: 22,617
- ann:page: 789
- kitsu:anime: 22,494
- kitsu:episodes: 280,137
- shikimori:anime: 24,009
- shikimori:detail: 23,602
- shikimori:related: 23,580
- shikimori:roles: 23,580
- wikidata:item: 8,561

## Data objects

- characters: 283,477
- staff: 535,642
- episodes: 276,763
- relationships: 39,226
- descriptions: 63,396
- qa_pairs: 317,907
- instructions: 235,395
- rag_chunks: 206,906
- alt_titles: 135,425
- anime_genres: 74,870
- anime_themes: 139,413
- anime_studios: 59,628
- splits: 35,766
- provenance: 153,892
- license_tiers: 35,766
- franchises: 23,980
- franchise_rows: 35,766
- studios: 2,966
- genres: 43
- themes: 422

## Derived text

### Question types (317,907 pairs, 29 types)

- type: 24,430
- air_date: 22,797
- episode_count: 22,779
- japanese_title: 22,452
- synopsis: 21,521
- runtime: 20,705
- alt_titles: 20,300
- genres: 17,347
- studio: 13,204
- score: 12,436
- source: 11,449
- english_title: 10,438
- favourites: 9,735
- themes: 9,586
- characters: 9,428
- character_role: 9,265
- director: 8,989
- franchise: 8,131
- relationship_reverse: 8,027
- relationship: 7,956
- multi_hop_episodes: 7,749
- multi_hop_studio: 6,310
- composer: 5,268
- writer: 5,173
- episode_title: 1,691
- unknown_score: 368
- unknown_studio: 325
- unknown_episodes: 42
- voice_actor: 6

### Instruction types (235,395 examples, 12 types)

- record_summarization: 35,766
- metadata_extraction: 34,991
- json_repair: 34,530
- title_normalization: 34,430
- staff_credits: 23,284
- relation_extraction: 17,948
- character_extraction: 17,917
- franchise_grouping: 11,876
- comparison: 11,434
- entity_resolution: 8,413
- episode_list: 3,405
- abstention: 1,401

### Descriptions (63,396)

- record_summary: 35,766
- source_synopsis: 27,630

### RAG chunk families (206,906)

- record_summary: 35,609
- characters: 34,737
- title_aliases: 33,465
- staff: 31,096
- relations: 28,809
- source_synopsis: 27,114
- voice_cast: 11,709
- episodes: 4,367

## Splits (90/5/5, seed 42, assigned per anime to prevent leakage)

- test: 1,789
- train: 32,189
- val: 1,788

## License tiers

- unresolved: 23,467
- permission_required: 11,330
- cc0_only: 969

Tier meanings, obligations and subset filters are in `exports/license_manifest.json`.

## Validation

- [PASS] min_anime_titles: 35766 unique anime with titles (required 20000, target 50000)
- [PASS] unique_source_remote_ids: 0 duplicated (source, remote_id) pairs
- [PASS] referential_integrity: no orphans
- [PASS] no_duplicate_title_year: 0 same-title+year collisions; 1874 rows with no year not compared
- [PASS] enum_conformance: type=[] status=[] season=[] source_material=[] age_rating=[] role=[] relation=[]
- [PASS] value_ranges: zero_scores=0 out_of_range_scores=0 bad_years=0 bad_episode_counts=0
- [PASS] entity_duplicates: characters=0 staff=0 relationships=0 alt_titles=0 episodes=0
- [PASS] name_field_semantics: 0 Cyrillic values still in name_native; 4119 characters with neither native nor localized name
- [PASS] relationship_integrity: self_loops=0 dangling_targets=0
- [PASS] split_coverage: 35766 split rows for 35766 anime, 0 duplicates
- [PASS] split_proportions: {'test': 1789, 'train': 32189, 'val': 1788} of 35766
- [PASS] qa_grounding: 317907 pairs, 0 ungrounded, 0 unresolved placeholders, 0 leaked sentinels
- [PASS] qa_fields_resolve: 0 unresolved of 5000 sampled pairs; examples []
- [PASS] qa_diversity: 29 question types, 41 templates, largest template share 0.0%
- [PASS] instruction_input_grounding: 235395 rows, 0 empty inputs, 0 sampled output values absent from input; examples []
- [PASS] instruction_diversity: 12 instruction types, largest share 0.0%
- [PASS] rag_chunk_quality: 206906 chunks, 0 under 30 chars, 0 not ending in a sentence stop, 0 without source refs, 0 raw JSON dumps, 0 without a kind label
- [PASS] license_tier_coverage: 35766/35766 anime tiered, 0 unknown tier values
- [PASS] provenance_coverage: 35766/35766 anime have at least one source link
- [PASS] required_title_fields: 0 anime without any title
- [PASS] prose_attribution: 184,054 prose rows; unlabelled=0; cc0 conflicts=0; problems=[]
- [PASS] export_schema: missing files=[] missing columns=[] empty despite source rows=[] prose export=[]

## Licensing & provenance

- AniList: public GraphQL API. Its terms permit API use but not redistribution of the
  content, and they prohibit hoarding or mass collection. Records that depend on AniList
  fields are tiered `permission_required` and must not be published without written
  permission.
- Kitsu: public JSON:API. No licence or redistribution grant could be located; the data
  is used under Kitsu's terms. Records that depend on Kitsu fields are tiered
  `permission_required`.
- Shikimori: a user agreement was located at shikimori.io/terms, but it grants no
  data-reuse right. Records are tiered `unresolved` and must not be redistributed.
- Wikidata: CC0-1.0, no obligations.
- ANN encyclopedia pages: copyrighted. 789 sample pages are retained in raw storage
  and linked to zero exported rows.
- MyAnimeList / Jikan: unreachable from the collection environment; excluded.
- **Upstream prose is retained with attribution.** 27,630 synopses, 84,329
  character biographies and 44,465 episode summaries ship with `prose_source` and
  `prose_license`. They are third-party expression, excluded from the project's
  CC-BY-4.0 grant, and remain subject to the named source's terms. Attribution is
  not permission. Per-source owners and terms are in `exports/attribution.json`.
- The tier describes the dataset's provenance obligation, not the copyright status of
  the underlying anime works, which remains with their rights holders.

## Limitations (measured)

- **Episode lists cover 21,604 of 35,766 anime (60.4%).** Kitsu is the only reachable source that publishes
  per-episode records; Shikimori's episode endpoint is unavailable, AniList supplies
  counts only, and MAL/Jikan is network-blocked. Raising this share needs a source
  that is not reachable from this environment.
- **Depth fields are uneven by design.** Characters, staff and episodes exist only
  where an upstream source published them; the field-coverage table above gives the
  exact rate per field rather than an average that hides the spread.
- **ANN contributes no rows.** The encyclopaedia is reachable only page-by-page and
  was sampled; nothing from it was linked into the exports.
- **Synthetic descriptions add no plot facts.** `record_summary` text is assembled
  only from structured fields of the same record. Upstream synopses, character bios
  and episode summaries are retained separately, labelled with `prose_source` and
  `prose_license`, and excluded from the project's CC-BY-4.0 grant.
- **QA and instruction rows are template-generated.** They are grounded and
  verifiable, but they are not human-written; treat them as supervision for
  extraction and grounding, not as a source of new facts.
- **The 50,000-title target is not met.** The union of
  the reachable catalogues is exhausted; MAL would raise it and is blocked.

## Phase log (last 50 entries)

- 2026-10-25T12:44:07+00:00 [enrich] kitsu episodes 20100/21740 anime eps=244838 ({'requests': 0, 'cache_hits': 27725, 'errors': 0})
- 2026-10-25T12:44:08+00:00 [enrich] kitsu episodes 20200/21740 anime eps=246058 ({'requests': 0, 'cache_hits': 27858, 'errors': 0})
- 2026-10-25T12:44:11+00:00 [enrich] kitsu episodes 20300/21740 anime eps=249230 ({'requests': 0, 'cache_hits': 28092, 'errors': 0})
- 2026-10-25T12:44:12+00:00 [enrich] kitsu episodes 20400/21740 anime eps=250211 ({'requests': 0, 'cache_hits': 28214, 'errors': 0})
- 2026-10-25T12:44:12+00:00 [enrich] kitsu episodes 20500/21740 anime eps=250668 ({'requests': 0, 'cache_hits': 28321, 'errors': 0})
- 2026-10-25T12:44:13+00:00 [enrich] kitsu episodes 20600/21740 anime eps=252805 ({'requests': 0, 'cache_hits': 28516, 'errors': 0})
- 2026-10-25T12:44:13+00:00 [enrich] kitsu episodes 20700/21740 anime eps=253723 ({'requests': 0, 'cache_hits': 28647, 'errors': 0})
- 2026-10-25T12:44:14+00:00 [enrich] kitsu episodes 20800/21740 anime eps=257779 ({'requests': 0, 'cache_hits': 28933, 'errors': 0})
- 2026-10-25T12:44:14+00:00 [enrich] kitsu episodes 20900/21740 anime eps=258860 ({'requests': 0, 'cache_hits': 29067, 'errors': 0})
- 2026-10-25T12:44:15+00:00 [enrich] kitsu episodes 21000/21740 anime eps=260432 ({'requests': 0, 'cache_hits': 29229, 'errors': 0})
- 2026-10-25T12:44:16+00:00 [enrich] kitsu episodes 21100/21740 anime eps=261080 ({'requests': 0, 'cache_hits': 29348, 'errors': 0})
- 2026-10-25T12:44:19+00:00 [enrich] kitsu episodes 21200/21740 anime eps=264214 ({'requests': 0, 'cache_hits': 29588, 'errors': 0})
- 2026-10-25T12:44:20+00:00 [enrich] kitsu episodes 21300/21740 anime eps=265728 ({'requests': 0, 'cache_hits': 29743, 'errors': 0})
- 2026-10-25T12:44:21+00:00 [enrich] kitsu episodes 21400/21740 anime eps=266108 ({'requests': 0, 'cache_hits': 29852, 'errors': 0})
- 2026-10-25T12:44:21+00:00 [enrich] kitsu episodes 21500/21740 anime eps=266823 ({'requests': 0, 'cache_hits': 29970, 'errors': 0})
- 2026-10-25T12:44:22+00:00 [enrich] kitsu episodes 21600/21740 anime eps=268203 ({'requests': 0, 'cache_hits': 30124, 'errors': 0})
- 2026-10-25T12:44:23+00:00 [enrich] kitsu episodes 21700/21740 anime eps=269656 ({'requests': 0, 'cache_hits': 30278, 'errors': 0})
- 2026-10-25T12:44:24+00:00 [enrich] kitsu episodes finished anime=21740 eps=269932 ({'requests': 0, 'cache_hits': 30322, 'errors': 0})
- 2026-10-25T12:47:53+00:00 [entities] anilist_full=22257 shikimori=23602 roles=711191 episodes=280137 kitsu=22494
- 2026-10-25T12:52:17+00:00 [normalize] {"anime_duplicates": {"merged": 0, "clusters": 0}, "anime_fields": {"anime_rows_changed": 12919}, "alt_titles": {"alt_titles_before": 333915, "alt_titles_after": 135425, "removed": 198490}, "relationships": {"relationships_before": 26719, "relationships_after": 26719, "removed": 0}, "characters": {"characters_before": 356592, "characters_after": 283477, "removed": 73115, "with_description": 84329, "with_voice_actors": 106521}, "staff": {"staff_before": 596140, "staff_after": 535642, "removed": 60498}, "episodes": {"episodes_before": 276772, "episodes_after": 276763, "removed": 9}, "reference": {"genres": 43, "themes": 422, "studios": 2966, "merged": {"genres": 0, "themes": 0, "studios": 7}}}
- 2026-10-25T12:52:31+00:00 [relationships] rows=39226
- 2026-10-25T12:52:35+00:00 [franchise] edges=28440 franchises=23980 multi_member=3380
- 2026-10-25T12:52:48+00:00 [descriptions] record_summary=35766
- 2026-10-25T12:54:06+00:00 [qa] items=305175 across 35766 anime
- 2026-10-25T13:01:07+00:00 [instructions] items=235395 types=12
- 2026-10-25T13:02:23+00:00 [rag] chunks=179792 kinds={'record_summary': 35609, 'title_aliases': 33465, 'characters': 34737, 'voice_cast': 11709, 'staff': 31096, 'episodes': 4367, 'relations': 28809}
- 2026-10-25T13:02:27+00:00 [split] total=35766 {'test': 1789, 'train': 32189, 'val': 1788}
- 2026-10-25T13:04:42+00:00 [export] {"anime": 35766, "characters": 283477, "staff": 535642, "studios": 2966, "genres": 43, "themes": 422, "episodes": 276763, "relationships": 39226, "qa": 305175, "instructions": 235395, "rag_chunks": 179792, "alt_titles": 135425, "descriptions": 35766, "entity_links": 77681, "franchises": 35766, "dedup_merge_log": 35768, "provenance": 153892, "sources": 6, "license_tiers": 35766, "anime_csv": 35766, "parquet": 10, "sqlite_export": 1}
- 2026-10-25T13:05:03+00:00 [validate] pass: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'export_schema': True}
- 2026-10-25T13:05:16+00:00 [checksums] files=36
- 2026-10-25T13:05:22+00:00 [report] unique=35766 min_gate=True target_met=False
- 2026-10-25T13:07:33+00:00 [validate] pass: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'export_schema': True}
- 2026-10-25T16:34:39+00:00 [checksums] files=36
- 2026-10-25T16:34:58+00:00 [checksums] files=36
- 2026-10-25T16:36:03+00:00 [validate] pass: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'export_schema': True}
- 2026-10-25T16:36:16+00:00 [report] unique=35766 min_gate=True target_met=False
- 2026-10-25T17:39:55+00:00 [descriptions] record_summary=35766 source_synopsis=27630
- 2026-10-25T17:41:54+00:00 [qa] items=317907 across 35766 anime
- 2026-10-25T17:43:39+00:00 [rag] chunks=206906 kinds={'record_summary': 35609, 'source_synopsis': 27114, 'title_aliases': 33465, 'characters': 34737, 'voice_cast': 11709, 'staff': 31096, 'episodes': 4367, 'relations': 28809}
- 2026-10-25T17:47:12+00:00 [export] {"anime": 35766, "characters": 283477, "staff": 535642, "studios": 2966, "genres": 43, "themes": 422, "episodes": 276763, "relationships": 39226, "qa": 317907, "instructions": 235395, "rag_chunks": 206906, "alt_titles": 135425, "descriptions": 63396, "entity_links": 77681, "franchises": 35766, "dedup_merge_log": 35768, "provenance": 153892, "sources": 6, "attribution": 6, "license_tiers": 35766, "anime_csv": 35766, "parquet": 10, "sqlite_export": 1}
- 2026-10-25T17:49:58+00:00 [validate] fail: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': False, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'prose_attribution': True, 'export_schema': True}
- 2026-10-25T17:50:53+00:00 [validate] pass: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'prose_attribution': True, 'export_schema': True}
- 2026-10-25T18:05:26+00:00 [export] {"anime": 35766, "characters": 283477, "staff": 535642, "studios": 2966, "genres": 43, "themes": 422, "episodes": 276763, "relationships": 39226, "qa": 317907, "instructions": 235395, "rag_chunks": 206906, "alt_titles": 135425, "descriptions": 63396, "entity_links": 77681, "franchises": 35766, "dedup_merge_log": 35768, "provenance": 153892, "sources": 6, "attribution": 7, "license_tiers": 35766, "anime_csv": 35766, "parquet": 10, "sqlite_export": 1}
- 2026-10-25T18:05:59+00:00 [validate] pass: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'prose_attribution': True, 'export_schema': True}
- 2026-10-25T18:06:15+00:00 [report] unique=35766 min_gate=True target_met=False
- 2026-10-25T18:08:38+00:00 [checksums] files=37
- 2026-10-25T18:14:36+00:00 [report] unique=35766 min_gate=True target_met=False
- 2026-10-25T18:17:37+00:00 [checksums] files=37
- 2026-10-25T18:21:18+00:00 [validate] pass: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'prose_attribution': True, 'export_schema': True}
- 2026-10-25T18:24:00+00:00 [validate] pass: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'prose_attribution': True, 'export_schema': True}
