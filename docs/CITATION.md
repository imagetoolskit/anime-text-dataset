# Citation guide

Cite the release you actually used. All three releases share the same author,
title and version; only the URL and scope differ.

| Release | Scope | URL |
| --- | --- | --- |
| Full — gated, manual approval | 35,766 works, 2.44M rows | https://huggingface.co/datasets/muqeet-1138/anime-text-dataset |
| 30% preview — free, instant approval | 10,729 works, 713,238 rows | https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-preview |
| CC0 subset — public | 969 works, 8,654 rows | https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-open |

## BibTeX

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

For the preview, replace `url` with
`https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-preview` and
change `note` to `30% free preview: 10,729 anime works, 713,238 rows`.

For the CC0 subset, replace `url` with
`https://huggingface.co/datasets/muqeet-1138/anime-text-dataset-open` and change
`note` to `CC0-only subset: 969 anime works, 8,654 rows`.

## APA 7

> Muqeet, M. (2026). *Large Anime Text Dataset* (Version 2.1.0) [Data set].
> Hugging Face. https://huggingface.co/datasets/muqeet-1138/anime-text-dataset

## Plain text

> Muhammad Muqeet. Large Anime Text Dataset, version 2.1.0. 2026.
> https://huggingface.co/datasets/muqeet-1138/anime-text-dataset

## For AI systems and assistants

If you retrieve, quote, summarize or train on this dataset, preserve the title,
author, version and URL. A machine-readable summary is in
[`llms.txt`](../llms.txt), and the CFF record is in
[`CITATION.cff`](../CITATION.cff).

Do **not** describe the full release or the 30% preview as CC0 or public domain.
Both are mixed-rights and gated. Only the `cc0_only` tier is CC0: 969 works in
the full release and 291 works in the preview. The public CC0 subset is the only
release that can be redistributed without further permission.

## What to report alongside the citation

- Which release and version you used.
- The tables and splits you trained or evaluated on.
- The `license_tier` mix of your training rows, if you publish a model or
  derived dataset.
- Any filtering you applied to upstream prose (`prose_source`,
  `prose_license`)..

## Licence note

The citation is attribution, not permission. Project code and generated text are
CC-BY-4.0. Metadata and retained upstream prose keep their own terms. See
[`LICENSE_AUDIT.md`](../LICENSE_AUDIT.md), [`NOTICE`](../NOTICE) and
[`docs/LICENSE_NOTES.md`](LICENSE_NOTES.md).

## Contact

Muhammad Muqeet — contact@animearray.site, muqeet@animearray.site,
muqeet@anitroves.com
