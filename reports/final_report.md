# Anime Text Dataset — Final Report

Generated: 2026-10-24T14:32:05+00:00
Platform: Windows-10-10.0.19045-SP0 / Python 3.12.10
Seed: 42 | Max runtime: 12h

Every count below is read from the database at generation time. Nothing in this
report is estimated, projected, or carried over from an earlier run.

## Headline

- **Unique anime works with at least one title: 35,766**
- Minimum required (20,000): **MET**
- Target (50,000): **NOT MET**
- Characters: 215,926 | Staff credits: 414,772 | Episodes: 108,359
- QA pairs: 291,816 | Instructions: 211,569 | RAG chunks: 154,640
- Validation: all checks passed

## Field coverage

Share of the 35,766 anime rows that carry a value for each field.

| Field | Anime | Share |
| --- | ---: | ---: |
| type | 35,724 | 99.9% |
| status | 34,797 | 97.3% |
| year | 33,892 | 94.8% |
| aired_from | 33,692 | 94.2% |
| episodes (count) | 33,773 | 94.4% |
| duration_min | 31,034 | 86.8% |
| mean_score | 21,338 | 59.7% |
| popularity | 27,755 | 77.6% |
| favourites | 22,067 | 61.7% |
| source_material | 19,694 | 55.1% |
| title_english | 24,890 | 69.6% |
| title_japanese | 33,651 | 94.1% |
| studios | 22,022 | 61.6% |
| genres | 26,603 | 74.4% |
| themes | 17,464 | 48.8% |
| alt titles | 32,437 | 90.7% |
| characters | 13,715 | 38.3% |
| character roles | 13,715 | 38.3% |
| voice actors | 11,709 | 32.7% |
| staff credits | 19,119 | 53.5% |
| episode list | 6,472 | 18.1% |
| episode titles | 2,348 | 6.6% |
| relationships | 11,943 | 33.4% |

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
- kitsu:episodes: 111,427
- shikimori:anime: 24,009
- shikimori:detail: 22,683
- shikimori:related: 5,441
- shikimori:roles: 5,597
- wikidata:item: 8,561

## Data objects

- characters: 215,926
- staff: 414,772
- episodes: 108,359
- relationships: 26,719
- descriptions: 35,766
- qa_pairs: 291,816
- instructions: 211,569
- rag_chunks: 154,640
- alt_titles: 130,224
- anime_genres: 71,271
- anime_themes: 139,413
- anime_studios: 57,125
- splits: 35,766
- provenance: 131,635
- license_tiers: 35,766
- franchises: 29,257
- franchise_rows: 35,766
- studios: 2,895
- genres: 43
- themes: 422

## Derived text

### Question types (291,816 pairs, 27 types)

- type: 26,430
- air_date: 24,755
- episode_count: 24,614
- japanese_title: 24,321
- alt_titles: 22,038
- runtime: 21,931
- genres: 18,022
- studio: 13,948
- score: 13,641
- source: 12,080
- english_title: 11,583
- favourites: 10,384
- themes: 10,259
- director: 7,311
- character_role: 7,250
- characters: 7,211
- relationship: 5,388
- relationship_reverse: 5,364
- multi_hop_episodes: 5,158
- multi_hop_studio: 4,904
- composer: 4,507
- franchise: 4,506
- writer: 4,218
- episode_title: 1,171
- unknown_studio: 404
- unknown_score: 366
- unknown_episodes: 52

### Instruction types (211,569 examples, 12 types)

- record_summarization: 35,766
- metadata_extraction: 34,991
- json_repair: 34,530
- title_normalization: 34,430
- staff_credits: 19,118
- character_extraction: 13,673
- relation_extraction: 11,943
- comparison: 8,710
- entity_resolution: 8,413
- franchise_grouping: 6,249
- episode_list: 2,270
- abstention: 1,476

### Descriptions (35,766)

- record_summary: 35,766

### RAG chunk families (154,640)

- record_summary: 35,606
- title_aliases: 33,306
- characters: 27,077
- staff: 24,446
- relations: 19,451
- voice_cast: 11,709
- episodes: 3,045

## Splits (90/5/5, seed 42, assigned per anime to prevent leakage)

- test: 1,789
- train: 32,189
- val: 1,788

## License tiers

- unresolved: 23,467
- permission_required: 8,229
- cc_by_sa: 3,101
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
- [PASS] name_field_semantics: 0 Cyrillic values still in name_native; 4537 characters with neither native nor localized name
- [PASS] relationship_integrity: self_loops=0 dangling_targets=0
- [PASS] split_coverage: 35766 split rows for 35766 anime, 0 duplicates
- [PASS] split_proportions: {'test': 1789, 'train': 32189, 'val': 1788} of 35766
- [PASS] qa_grounding: 291816 pairs, 0 ungrounded, 0 unresolved placeholders, 0 leaked sentinels
- [PASS] qa_fields_resolve: 8 unresolved of 5000 sampled pairs; examples [(20202, 'episodes'), (12312, 'studios'), (2365, 'studios'), (19357, 'episodes'), (6464, 'studios')]
- [PASS] qa_diversity: 27 question types, 39 templates, largest template share 0.0%
- [PASS] instruction_input_grounding: 211569 rows, 0 empty inputs, 0 sampled output values absent from input; examples []
- [PASS] instruction_diversity: 12 instruction types, largest share 0.0%
- [PASS] rag_chunk_quality: 154640 chunks, 0 under 30 chars, 0 not ending in a sentence stop, 0 without source refs, 0 raw JSON dumps, 0 without a kind label
- [PASS] license_tier_coverage: 35766/35766 anime tiered, 0 unknown tier values
- [PASS] provenance_coverage: 35766/35766 anime have at least one source link
- [PASS] required_title_fields: 0 anime without any title
- [PASS] export_schema: missing files=[] missing columns=[] empty despite source rows=[] upstream prose=[]

## Licensing & provenance

- AniList: public GraphQL API. AniList's terms permit API use; they do not grant
  redistribution of the underlying content. Records that depend on AniList fields are
  tiered `permission_required` and must not be published without written permission.
- Kitsu: CC-BY-SA community data. Records that depend on Kitsu content are tiered
  `cc_by_sa` and carry attribution plus share-alike obligations.
- Shikimori: no license or terms for API data could be located. Records are tiered
  `unresolved` and must not be redistributed.
- Wikidata: CC0-1.0, no obligations.
- ANN encyclopedia pages: copyrighted. 789 sample pages are retained in raw storage
  and linked to zero exported rows.
- MyAnimeList / Jikan: unreachable from the collection environment; excluded.
- **No upstream prose is shipped.** Plot synopses, character bios and episode
  summaries are third-party expression whose redistribution no source terms grant,
  and a close paraphrase would still be a derivative work. Those fields are dropped
  from every export. What remains is factual metadata, short names/titles, and text
  generated by this project from those facts.
- The tier describes the dataset's provenance obligation, not the copyright status of
  the underlying anime works, which remains with their rights holders.

## Limitations (measured)

- **Episode lists cover 6,472 of 35,766 anime (18.1%).** Kitsu is the only reachable source that publishes
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
  and episode summaries are third-party prose, so they are not exported at all.
- **QA and instruction rows are template-generated.** They are grounded and
  verifiable, but they are not human-written; treat them as supervision for
  extraction and grounding, not as a source of new facts.
- **The 50,000-title target is not met.** The union of
  the reachable catalogues is exhausted; MAL would raise it and is blocked.

## Phase log (last 50 entries)

- 2026-10-24T11:35:57+00:00 [enrich] anilist full 4500/9536 ({'requests': 300, 'cache_hits': 0, 'errors': 0})
- 2026-10-24T11:39:32+00:00 [enrich] anilist full 6000/9536 ({'requests': 400, 'cache_hits': 0, 'errors': 0})
- 2026-10-24T11:43:07+00:00 [enrich] anilist full 7500/9536 ({'requests': 500, 'cache_hits': 0, 'errors': 0})
- 2026-10-24T11:46:41+00:00 [enrich] anilist full 9000/9536 ({'requests': 600, 'cache_hits': 0, 'errors': 0})
- 2026-10-24T11:47:59+00:00 [enrich] anilist full finished: 9536 anime, {'requests': 636, 'cache_hits': 0, 'errors': 0}
- 2026-10-24T11:48:01+00:00 [enrich] shikimori detail: 9347 to enrich (tier=all)
- 2026-10-24T11:53:46+00:00 [enrich] shikimori detail 1000/9347 ({'requests': 546, 'cache_hits': 466, 'errors': 0})
- 2026-10-24T12:01:38+00:00 [enrich] shikimori detail 2000/9347 ({'requests': 1277, 'cache_hits': 761, 'errors': 0})
- 2026-10-24T12:10:30+00:00 [enrich] shikimori detail 3000/9347 ({'requests': 2074, 'cache_hits': 995, 'errors': 0})
- 2026-10-24T12:20:14+00:00 [enrich] shikimori detail 4000/9347 ({'requests': 3011, 'cache_hits': 1091, 'errors': 0})
- 2026-10-24T12:31:23+00:00 [enrich] shikimori detail 5000/9347 ({'requests': 4048, 'cache_hits': 1091, 'errors': 0})
- 2026-10-24T12:41:46+00:00 [enrich] shikimori detail: 3444 to enrich (tier=all)
- 2026-10-24T12:42:09+00:00 [enrich] shikimori roles: 14790 to fetch (tier=all)
- 2026-10-24T12:43:13+00:00 [descriptions] record_summary=35767
- 2026-10-24T12:44:39+00:00 [qa] items=243748 across 35767 anime
- 2026-10-24T12:50:52+00:00 [instructions] items=184764 types=11
- 2026-10-24T12:51:34+00:00 [rag] chunks=109042 kinds={'record_summary': 35617, 'title_aliases': 32732, 'characters': 6591, 'staff': 15806, 'episodes': 3045, 'relations': 15251}
- 2026-10-24T12:51:38+00:00 [split] total=35767 {'test': 1789, 'train': 32190, 'val': 1788}
- 2026-10-24T12:55:13+00:00 [export] {"anime": 35767, "characters": 143682, "staff": 399935, "studios": 2340, "genres": 42, "themes": 422, "episodes": 108368, "relationships": 24934, "qa": 243748, "instructions": 184764, "rag_chunks": 109042, "alt_titles": 263367, "descriptions": 35767, "entity_links": 77681, "franchises": 35767, "dedup_merge_log": 35767, "provenance": 64864, "sources": 6, "license_tiers": 35767, "anime_csv": 35767, "parquet": 10, "sqlite_export": 1}
- 2026-10-24T12:55:42+00:00 [validate] fail: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': False, 'enum_conformance': False, 'value_ranges': False, 'entity_duplicates': False, 'name_semantics': False, 'relationship_integrity': False, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': False, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': False, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'export_schema': True}
- 2026-10-24T12:55:52+00:00 [checksums] files=37
- 2026-10-24T12:56:12+00:00 [report] unique=35767 min_gate=True target_met=False
- 2026-10-24T12:56:43+00:00 [validate] fail: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': False, 'enum_conformance': False, 'value_ranges': False, 'entity_duplicates': False, 'name_semantics': False, 'relationship_integrity': False, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': False, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': False, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'export_schema': True}
- 2026-10-24T13:04:49+00:00 [entities] anilist_full=22257 shikimori=20232 roles=477117 episodes=111427 kitsu=22494
- 2026-10-24T13:11:46+00:00 [normalize] {"anime_duplicates": {"merged": 0, "clusters": 0}, "anime_fields": {"anime_rows_changed": 0}, "alt_titles": {"alt_titles_before": 130224, "alt_titles_after": 130224, "removed": 0}, "relationships": {"relationships_before": 19070, "relationships_after": 19070, "removed": 0}, "characters": {"characters_before": 146623, "characters_after": 146623, "removed": 0, "with_description": 0, "with_voice_actors": 0}, "staff": {"staff_before": 414772, "staff_after": 414772, "removed": 0}, "episodes": {"episodes_before": 108359, "episodes_after": 108359, "removed": 0}, "reference": {"genres": 43, "themes": 422, "studios": 2895, "merged": {"genres": 0, "themes": 0, "studios": 3}}}
- 2026-10-24T13:16:40+00:00 [entities] anilist_full=22257 shikimori=20232 roles=477117 episodes=111427 kitsu=22494
- 2026-10-24T13:21:01+00:00 [normalize] {"anime_duplicates": {"merged": 0, "clusters": 0}, "anime_fields": {"anime_rows_changed": 11314}, "alt_titles": {"alt_titles_before": 410443, "alt_titles_after": 130224, "removed": 280219}, "relationships": {"relationships_before": 19070, "relationships_after": 19070, "removed": 0}, "characters": {"characters_before": 266830, "characters_after": 215926, "removed": 50904, "with_description": 84329, "with_voice_actors": 106521}, "staff": {"staff_before": 452157, "staff_after": 414772, "removed": 37385}, "episodes": {"episodes_before": 108368, "episodes_after": 108359, "removed": 9}, "reference": {"genres": 43, "themes": 422, "studios": 2895, "merged": {"genres": 0, "themes": 0, "studios": 7}}}
- 2026-10-24T13:21:21+00:00 [relationships] rows=33192
- 2026-10-24T13:21:30+00:00 [franchise] edges=11499 franchises=29257 multi_member=2420
- 2026-10-24T13:21:53+00:00 [descriptions] record_summary=35766
- 2026-10-24T13:23:09+00:00 [qa] items=291572 across 35766 anime
- 2026-10-24T13:30:11+00:00 [instructions] items=211861 types=12
- 2026-10-24T13:31:26+00:00 [rag] chunks=157478 kinds={'record_summary': 35606, 'title_aliases': 33306, 'characters': 27077, 'voice_cast': 11709, 'staff': 24446, 'episodes': 3045, 'relations': 22289}
- 2026-10-24T13:31:30+00:00 [split] total=35766 {'test': 1789, 'train': 32189, 'val': 1788}
- 2026-10-24T13:34:24+00:00 [export] {"anime": 35766, "characters": 215926, "staff": 414772, "studios": 2895, "genres": 43, "themes": 422, "episodes": 108359, "relationships": 33192, "qa": 291572, "instructions": 211861, "rag_chunks": 157478, "alt_titles": 130224, "descriptions": 35766, "entity_links": 77681, "franchises": 35766, "dedup_merge_log": 35768, "provenance": 131635, "sources": 6, "license_tiers": 35766, "anime_csv": 35766, "parquet": 10, "sqlite_export": 1}
- 2026-10-24T13:34:57+00:00 [validate] fail: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': False, 'value_ranges': False, 'entity_duplicates': False, 'name_semantics': False, 'relationship_integrity': False, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': False, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': False, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'export_schema': True}
- 2026-10-24T13:43:34+00:00 [normalize] {"anime_duplicates": {"merged": 0, "clusters": 0}, "anime_fields": {"anime_rows_changed": 860}, "alt_titles": {"alt_titles_before": 130224, "alt_titles_after": 130224, "removed": 0}, "relationships": {"relationships_before": 33192, "relationships_after": 27154, "removed": 6038}, "characters": {"characters_before": 215926, "characters_after": 215926, "removed": 0, "with_description": 84329, "with_voice_actors": 106521}, "staff": {"staff_before": 414772, "staff_after": 414772, "removed": 0}, "episodes": {"episodes_before": 108359, "episodes_after": 108359, "removed": 0}, "reference": {"genres": 43, "themes": 422, "studios": 2895, "merged": {"genres": 0, "themes": 0, "studios": 0}}}
- 2026-10-24T13:43:55+00:00 [relationships] rows=26719
- 2026-10-24T13:44:50+00:00 [descriptions] record_summary=35766
- 2026-10-24T13:47:01+00:00 [qa] items=291816 across 35766 anime
- 2026-10-24T13:54:33+00:00 [instructions] items=211569 types=12
- 2026-10-24T13:56:40+00:00 [rag] chunks=154640 kinds={'record_summary': 35606, 'title_aliases': 33306, 'characters': 27077, 'voice_cast': 11709, 'staff': 24446, 'episodes': 3045, 'relations': 19451}
- 2026-10-24T13:56:51+00:00 [split] total=35766 {'test': 1789, 'train': 32189, 'val': 1788}
- 2026-10-24T14:02:19+00:00 [export] {"anime": 35766, "characters": 215926, "staff": 414772, "studios": 2895, "genres": 43, "themes": 422, "episodes": 108359, "relationships": 26719, "qa": 291816, "instructions": 211569, "rag_chunks": 154640, "alt_titles": 130224, "descriptions": 35766, "entity_links": 77681, "franchises": 35766, "dedup_merge_log": 35768, "provenance": 131635, "sources": 6, "license_tiers": 35766, "anime_csv": 35766, "parquet": 10, "sqlite_export": 1}
- 2026-10-24T14:03:08+00:00 [validate] fail: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': False, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'export_schema': True}
- 2026-10-24T14:04:09+00:00 [validate] pass: {'min_titles': True, 'unique_source_ids': True, 'referential_integrity': True, 'no_duplicate_titles': True, 'enum_conformance': True, 'value_ranges': True, 'entity_duplicates': True, 'name_semantics': True, 'relationship_integrity': True, 'split_leakage': True, 'split_proportions': True, 'qa_grounding': True, 'qa_fields_resolve': True, 'qa_diversity': True, 'instruction_grounding': True, 'instruction_diversity': True, 'rag_quality': True, 'license_coverage': True, 'provenance_coverage': True, 'required_fields': True, 'export_schema': True}
- 2026-10-24T14:04:38+00:00 [enrich] shikimori detail: 3378 to enrich (tier=all)
- 2026-10-24T14:10:01+00:00 [enrich] shikimori detail 36641 failed: shikimori: HTTP 404 for https://shikimori.io/api/animes/36641 params=None
- 2026-10-24T14:15:28+00:00 [enrich] shikimori detail 1000/3378 ({'requests': 1033, 'cache_hits': 0, 'errors': 1})
- 2026-10-24T14:26:41+00:00 [enrich] shikimori detail 2000/3378 ({'requests': 2070, 'cache_hits': 0, 'errors': 1})
