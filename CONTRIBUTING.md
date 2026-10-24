# Contributing

Maintainer: **Muhammad Muqeet** — muqeet@animearray.site, muqeet@anitroves.com.

## Scope

This project collects factual anime metadata from public sources into a
text-only dataset. Contributions must respect the ground rules:

- No fabricated, duplicated, or padded records.
- No copyrighted long-form text (scripts, transcripts, subtitles, lyrics,
  manga, long reviews).
- Provenance and licensing must be recorded per record; uncertain status is
  recorded as uncertain.
- Never claim a license that has not been verified.

## Adding or fixing a source adapter

1. Read an existing adapter in `src/sources/` (`base.py` gives rate limiting,
   HTTP caching, and backoff).
2. Add your source to `config/config.json` (rate limits, runtime caps) and to
   the LICENSE_NOTES in `src/pipeline/discover.py`.
3. Register it in `exports/sources.jsonl` generation (`sources_registry()` in
   `src/pipeline/export.py`) with a full license/permission statement.
4. Never bypass rate limits; make the pipeline resumable via checkpointing.

## Pipeline changes

- Keep discovery separate from enrichment (per the spec).
- Every new stage should checkpoint (`cp_set`) and log (`log`).
- Generated/synthetic text must be labeled `synthetic=true` and retain its
  source record IDs.

## Testing

Run the end-to-end test on a small fabricated corpus (no network):

```bash
python tests/test_pipeline_e2e.py
python -m pytest tests/ -q
```

Add validation checks to `src/validate/validators.py` rather than ad-hoc
scripts.

## Releases

Follow the release checklist in `reports/final_report.md` and update
`CHANGELOG.md`. Include checksums in the release assets.