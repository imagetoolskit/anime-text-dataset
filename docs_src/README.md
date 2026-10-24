# Site source

The four HTML pages here are the editable source for the published site in
`docs/`. They contain count tokens such as `{{n:qa_pairs}}`, `{{r:qa_pairs}}`
(raw number, for JavaScript) and `{{v:version}}`.

Render them with:

```bash
python scripts/sync_docs.py
```

That command reads `reports/summary.json` (run `python -m src.cli report`
first), writes the rendered pages to `docs/`, and refreshes the generated
Markdown tables. `python scripts/sync_docs.py --check` exits non-zero when
`docs/` no longer matches `docs_src/` or the report.

Do not edit `docs/*.html` directly: the next render overwrites it. Edit the
matching file in this directory instead.
