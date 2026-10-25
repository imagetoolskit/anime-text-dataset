# License Notes & Publishability

This note explains what you may do with the dataset and its code. It is a
plain-language summary of the terms recorded in the release, **not legal
advice**. When in doubt, keep the attribution files (`NOTICE`,
`ACKNOWLEDGMENTS.md`, `exports/attribution.json`, `exports/sources.jsonl`,
`exports/provenance.jsonl`) and check the upstream terms for each source you
rely on.

---

## What the repository license covers

The repository is released as **CC-BY-4.0** (`LICENSE`). That covers the code
and the material this project generates:

- The aggregation, deduplication, normalization, canonicalization and
  cross-linking logic.
- The generated `record_summary` text, non-synopsis QA pairs, instruction
  examples, derived RAG chunks, splits, documentation and site.
- The code in `src/`, `scripts/`, `examples/` and `tests/`.

CC-BY-4.0 requires **attribution** when you share or adapt the material. The
simplest compliant way is to keep this repository's `CITATION.cff` or the
citation block in `README.md` with your work.

**CC-BY-4.0 cannot relicense upstream content.** Titles, cast names, factual
metadata, synopses and biographies come from third parties and stay under their
own terms. That is what the per-record license tiers and the per-field prose
attribution exist to express.

## Upstream prose is retained, attributed, and excluded from CC-BY

Plot synopses, character biographies, episode summaries and tag definitions are
creative expression. They carry real training signal, so they are kept rather
than deleted or paraphrased. They are **not** covered by this project's
CC-BY-4.0 grant and remain subject to the source that published them.

| Field | Rows | Source column | Export files |
| --- | ---: | --- | --- |
| `anime.synopsis` | 27,630 | `synopsis_source` | `anime.jsonl`, `anime.csv`, `anime.parquet`, SQLite `anime` |
| `characters.description` | 84,329 | `source` | `characters.jsonl`, SQLite `characters` |
| `episodes.synopsis` | 44,465 | `source` | `episodes.jsonl`, SQLite `episodes` |
| `themes.description` | 422 | `description_source` | `themes.jsonl`, SQLite `themes` |
| `descriptions.kind = 'source_synopsis'` | 27,630 | `source` | `descriptions.jsonl` |
| `rag_chunks.kind = 'source_synopsis'` | 27,114 | `prose_source` | `rag_chunks.jsonl` |
| `qa_pairs.qtype = 'synopsis'` | 21,521 | `prose_source` | `qa.jsonl` |

Every exported prose row carries `prose_source` (registry id) and
`prose_license` (`permission_required`, `unresolved`, or `allowed`). The
per-source registry is `exports/attribution.json`; the same block is embedded in
`exports/license_manifest.json` as `prose_attribution`.

All 27,630 synopses have a verified source label: Kitsu 20,715, AniList 5,157,
Shikimori 1,758. The `unknown` bucket exists for future unlabelled rows and is
tiered `unresolved`.

`python -m src.cli validate` checks that prose survives export with its
attribution, that no `cc0_only` row carries non-CC0 prose, and that the SQLite
release copy matches the working database's prose counts.

The artifact-by-artifact inventory, including what the maintainer does **not**
claim, is in [`../LICENSE_AUDIT.md`](../LICENSE_AUDIT.md).

## Source terms as recorded

Values below are recorded per source in `exports/sources.jsonl` and
`exports/attribution.json`, including the `retrieval_date` of the run that
supplied them. Terms pages were fetched on 2026-10-25.

| Source | Owner | Terms | Status recorded | Tier assigned |
| --- | --- | --- | --- | --- |
| **Wikidata** | Wikimedia Foundation / contributors | https://www.wikidata.org/wiki/Wikidata:Licensing | CC0-1.0 | `cc0_only` |
| **Kitsu** | Kitsu | https://kitsu.io/terms | Public JSON:API; no data-redistribution grant located | `permission_required` |
| **AniList** | AniList | https://anilist.co/terms | Content copyright its providers; API terms do not grant redistribution | `permission_required` |
| **Shikimori** | Shikimori | https://shikimori.io/terms | 2012 user agreement; no data-reuse grant | `unresolved` |
| **ANN Encyclopedia** | Anime News Network | no terms page located | Copyrighted | none — contributes no linked rows |
| **MyAnimeList / Jikan** | MyAnimeList | https://myanimelist.net/about/terms_of_use | Not collected | none — excluded |

Attribution is not permission. A source's name and terms URL identify the owner;
they do not grant redistribution.

## Redistribution tiers

Every anime row is assigned exactly one tier: the **strictest** implied by the
metadata and prose sources that contributed to it. Precedence is
`unresolved` > `permission_required` > `cc0_only`.

| Tier | Obligation | Permitted | Rows |
| --- | --- | --- | ---: |
| `unresolved` | Shikimori contributes (no data-reuse grant) or an unrecorded prose source exists. No permission basis identified. | Do not redistribute. | 23,467 |
| `permission_required` | AniList and Kitsu terms grant API use, not redistribution of content. Written permission is required before publishing derived records. | Internal use, research, and training subject to your own agreement with the rights holders. | 11,330 |
| `cc0_only` | None. CC0 waives copyright; attribution is courtesy. | Reuse freely. | 969 |

Exact per-tier counts, the tier definitions shown to consumers, the list of
known gaps and a disclaimer are written to `exports/license_manifest.json` on
every run. Per-anime assignments are in `exports/license_tiers.jsonl` and in the
`license_tier` column of every exported table. Ready-made id lists are in
`exports/license_tier_<tier>.csv`; `exports/license_commercial_clear.csv`
contains the `cc0_only` rows.

The tier describes **this dataset's provenance obligation**, not the copyright
status of the underlying anime, which remains with its rights holders.

## Practical rules of thumb

1. **Deriving QA, instructions or RAG data and training a model** on this
   package is the intended use. Keep attribution and describe the tier mix in
   your dataset or model card.
2. **Publishing a model** — only `cc0_only` rows have no upstream permission
   outstanding. Rows tiered `permission_required` or `unresolved` carry
   obligations this project cannot discharge for you.
3. **Redistributing the dataset or a subset** — filter on `license_tier` and
   `prose_license` first, and keep `NOTICE`, `ACKNOWLEDGMENTS.md`,
   `attribution.json`, `sources.jsonl` and `provenance.jsonl` alongside whatever
   you ship.
4. **Commercial products** — only 969 of 35,766 rows (2.7%) are `cc0_only`.
   Review the per-provider terms for any source-derived field you republish. The
   project-generated text stays usable under CC-BY-4.0; the dataset as a whole
   cannot be sold or offered commercially without permission.
5. **Prefer the generated text for low-risk use** — non-synopsis QA pairs,
   instruction examples, derived RAG chunks and `record_summary` descriptions
   are produced by this project from factual fields. They carry fewer
   obligations than upstream prose, which is why each prose row is labelled so
   you can filter it out.

## What the maintainer does not claim

- Copyright in upstream factual metadata, titles, names, prose, or the anime
  works.
- A sublicense from AniList, Kitsu, Shikimori or ANN (see the tiers above).
- That a `license_tier` or `prose_source` label is legal clearance. It labels an
  obligation; it does not discharge it.
- That database rights do not apply in your jurisdiction. Factual compilations
  can carry sui generis rights even when individual facts are free.

## Related files

- `LICENSE` — CC-BY-4.0 grant notice and scope boundary.
- `NOTICE` — attribution and source list.
- `exports/attribution.json` — owner, terms, prose fields and status per source.
- `exports/license_manifest.json` — tier definitions, counts, gaps and
  `prose_attribution`.
- `LICENSE_AUDIT.md` — artifact-by-artifact rights inventory.
