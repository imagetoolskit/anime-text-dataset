# License Notes & Publishability

This note explains what you may do with the dataset and its code. It is a
plain-language summary of the terms recorded in the release, **not legal
advice**. When in doubt, keep the attribution files (`NOTICE`,
`ACKNOWLEDGMENTS.md`, `exports/sources.jsonl`, `exports/provenance.jsonl`) and
check the upstream terms for each source you rely on.

---

## What the repository license covers

The repository is released as **CC-BY-4.0** (`LICENSE`). That covers the code
and the material this project generates:

- The aggregation, deduplication, normalization, canonicalization and
  cross-linking logic.
- The generated `record_summary` text, QA pairs, instruction examples, RAG
  chunks, splits, documentation and site.
- The code in `src/`, `scripts/`, `examples/` and `tests/`.

CC-BY-4.0 requires **attribution** when you share or adapt the material. The
simplest compliant way is to keep this repository's `CITATION.cff` or the
citation block in `README.md` with your work.

**CC-BY-4.0 cannot relicense upstream content.** Titles, cast names, factual
metadata and similar fields come from third parties and stay under their own
terms. That is what the per-record license tiers exist to express.

## Upstream prose is not in the release

Plot synopses, character biographies and episode summaries are creative
expression. No source in this pipeline grants redistribution, and a close
paraphrase would still be a derivative work, so the fields are **removed from
every export** rather than rewritten.

| Removed | Where it used to appear |
| --- | --- |
| `anime.synopsis`, `anime.synopsis_source` | `anime.jsonl`, `anime.csv`, `anime.parquet`, SQLite `anime` |
| `characters.description` | `characters.jsonl`, SQLite `characters` |
| `episodes.synopsis` | `episodes.jsonl`, SQLite `episodes` |
| `themes.description`, `genres.description` | `themes.jsonl`, `genres.jsonl`, SQLite reference tables |
| `descriptions.kind = 'source_synopsis'` | `descriptions.jsonl` |
| `rag_chunks.kind = 'source_synopsis'` | `rag_chunks.jsonl` |
| `qa_pairs.qtype = 'synopsis'` | `qa.jsonl` |

The local working database still holds those columns so collection can
deduplicate; `data/` is git-ignored and is not a release artifact.
`python -m src.cli validate` fails if a prose field reappears in an export.

The artifact-by-artifact inventory, including what the maintainer does **not**
claim, is in [`../LICENSE_AUDIT.md`](../LICENSE_AUDIT.md).

## Source terms as recorded

Values below are recorded per source in `exports/sources.jsonl`, including the
`retrieval_date` of the run that supplied them.

| Source | Recorded terms | Status recorded | Tier assigned |
| --- | --- | --- | --- |
| **Wikidata** | CC0-1.0 | `public_domain_cc0` | `cc0_only` |
| **Kitsu** | Public JSON:API; no license or redistribution grant for the data could be located | `public_api_terms` | `permission_required` |
| **AniList** | Content copyright its respective providers; the API terms permit retrieval and API use, not redistribution of the content | `public_api_no_auth` | `permission_required` |
| **Shikimori** | No license or terms for the API data could be located | `public_api_uncertain` | `unresolved` |
| **ANN Encyclopedia** | Copyrighted | `collected_but_not_integrated` | none — contributes no linked rows |
| **MyAnimeList / Jikan** | Not collected | `blocked` | none — excluded |

## Redistribution tiers

Every anime row is assigned exactly one tier: the **strictest** implied by the
sources that contributed to it. Precedence is
`unresolved` > `permission_required` > `cc0_only`.

| Tier | Obligation | Permitted | Rows |
| --- | --- | --- | --- |
| `unresolved` | Shikimori contributes and publishes no terms for its data. There is no permission basis identified. | Do not redistribute. | see `exports/license_manifest.json` |
| `permission_required` | AniList and Kitsu terms grant API use, not redistribution of content. Written permission from the provider and the underlying rights holders is required before publishing derived records. | Internal use, research, and training subject to your own agreement with the rights holders. | see manifest |
| `cc0_only` | None. CC0 waives copyright; attribution is courtesy. | Reuse freely. | see manifest |

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
3. **Redistributing the dataset or a subset** — filter on `license_tier` first,
   and keep `NOTICE`, `ACKNOWLEDGMENTS.md`, `sources.jsonl` and
   `provenance.jsonl` alongside whatever you ship.
4. **Commercial products** — review the per-provider terms (AniList, Kitsu,
   Shikimori) for any source-derived field you republish. The generated text
   stays usable under CC-BY-4.0.
5. **Prefer the generated text** — QA pairs, instruction examples, RAG chunks
   and `record_summary` descriptions are produced by this project from factual
   fields. They raise fewer questions than any upstream text, which is why no
   upstream text is shipped at all.

## What the maintainer does not claim

- Copyright in upstream factual metadata, titles, names or the anime works.
- A sublicense from AniList, Shikimori or ANN (see the tiers above).
- That a `license_tier` is legal clearance. It labels an obligation; it does
  not discharge it.
- That database rights do not apply in your jurisdiction. Factual compilations
  can carry sui generis rights even when individual facts are free.

## Related files

- `LICENSE` — CC-BY-4.0 legal text.
- `LICENSE_AUDIT.md` — per-artifact origin and rights inventory.
- `NOTICE` — required source-credit notice.
- `ACKNOWLEDGMENTS.md` — human-readable attribution.
- `exports/sources.jsonl` — per-source terms, status and retrieval date.
- `exports/provenance.jsonl` — per-record source, URL and license note.
- `exports/license_tiers.jsonl` — per-anime tier and reason.
- `exports/license_manifest.json` — tier definitions, counts, content policy, gaps, disclaimer.
- `CITATION.cff` — how to cite the release.
