"""Field-level attribution for upstream prose.

Upstream synopses, character biographies, episode summaries and tag
descriptions are third-party expression. They are retained in the release with
a recorded source and that source's terms. Attribution makes the obligation
visible and filterable; it does not itself grant redistribution.
"""

SOURCE_ALIASES = {
    "kitsu synopsis": "kitsu",
    "kitsu": "kitsu",
    "anilist": "anilist",
    "shikimori": "shikimori",
    "ann": "ann",
    "anime news network": "ann",
    "wikidata": "wikidata",
    "mal": "mal",
    "myanimelist": "mal",
}

# table -> (prose column, source column)
PROSE_FIELDS = {
    "anime": ("synopsis", "synopsis_source"),
    "characters": ("description", "source"),
    "episodes": ("synopsis", "source"),
    "themes": ("description", "description_source"),
    "descriptions": ("text", "source"),
    "qa_pairs": ("answer", "prose_source"),
    "rag_chunks": ("text", "prose_source"),
}


def normalize_source(value) -> str:
    """Map a stored provenance label to a registry source id.

    Unrecorded labels become ``unknown`` rather than being silently assigned
    to a plausible-looking source.
    """
    if value is None:
        return "unknown"
    key = str(value).strip().lower()
    if not key:
        return "unknown"
    if key in SOURCE_ALIASES:
        return SOURCE_ALIASES[key]
    for prefix in ("kitsu", "anilist", "shikimori", "ann", "wikidata", "mal"):
        if key.startswith(prefix):
            return prefix
    return "unknown"
