import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.pipeline.dedup import map_type, norm_title, year_of
from src.pipeline.facts import find_staff
from src.pipeline.normalize import (
    is_cyrillic,
    norm_key,
    norm_text,
    strip_html,
)
from src.pipeline.qa import fmt_date, join_list, plural


def test_norm_title_handles_case_punct_article():
    assert norm_title("The Cowboy Bebop!") == "thecowboybebop"
    assert norm_title("Cowboy Bebop: The Movie") == "cowboybebopthemovie"
    assert norm_title("Psycho-Pass: Case.3") == "psychopasscase3"
    assert norm_title(None) is None


def test_type_mapping_normalizes():
    assert map_type("TV") == "tv"
    assert map_type("MOVIE") == "movie"
    assert map_type("OVA") == "ova"
    assert map_type("MANGA") is None


def test_year_extraction_from_variants():
    assert year_of({"startDate": {"year": 2019, "month": 4, "day": 6}}) == 2019
    assert year_of({"aired_on": "2005-07-01"}) == 2005
    assert year_of({"seasonYear": 2021}) == 2021
    assert year_of({}) is None


# --- normalize -------------------------------------------------------------


def test_norm_text_collapses_and_trims():
    assert norm_text("  Cowboy\u00a0 Bebop  ") == "Cowboy Bebop"
    assert norm_text("\u200b") is None
    assert norm_text(None) is None


def test_strip_html_removes_tags_and_entities():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert strip_html("Rock &amp; Roll") == "Rock & Roll"
    assert strip_html("[link](https://example.com) text") == "link text"
    assert strip_html("") is None


def test_norm_key_ignores_case_punctuation_and_spacing():
    assert norm_key("Cowboy Bebop!") == norm_key("cowboy  bebop")
    assert norm_key("Steins;Gate") == norm_key("steins gate")
    assert norm_key(None) == ""


def test_cyrillic_detection():
    assert is_cyrillic("Джет Блэк")
    assert not is_cyrillic("Jet Black")
    assert not is_cyrillic("")


# --- staff role matching ---------------------------------------------------


def test_find_staff_excludes_nearby_credit_types():
    staff = [
        {"name": "Real Director", "roles": ["Director"]},
        {"name": "Episode Director", "roles": ["Episode Director"]},
        {"name": "ADR Director", "roles": ["ADR Director"]},
        {"name": "Assistant Director", "roles": ["Assistant Director"]},
        {"name": "Composer", "roles": ["Music"]},
    ]
    directors = find_staff(staff, ("director",), ("assistant", "episode", "adr", "dub"))
    assert directors == ["Real Director"]
    music = find_staff(staff, ("music", "composer"), ("producer", "theme"))
    assert music == ["Composer"]


# --- QA formatting helpers -------------------------------------------------


def test_plural_and_join_list():
    assert plural(1, "episode") == "1 episode"
    assert plural(12, "episode") == "12 episodes"
    assert join_list(["a"]) == "a"
    assert join_list(["a", "b"]) == "a and b"
    assert join_list(["a", "b", "c"]) == "a, b, and c"


def test_fmt_date_accepts_partial_and_rejects_nonsense():
    assert fmt_date("1998-04-03") == "3 April 1998"
    assert fmt_date("1998") == "1998"
    assert fmt_date("1998-13-40") == "1998"
    assert fmt_date(None) is None


# --- doc sync --------------------------------------------------------------

SUMMARY = {
    "version": "9.9.9",
    "unique_titles": 12345,
    "entity_links": 40000,
    "by_source": {"anilist": 10000, "kitsu": 9000, "shikimori": 11000,
                  "wikidata": 8000, "ann": 0},
    "raw_payloads": {"anilist:media_full": 10000, "wikidata:item": 8000,
                     "ann:page": 789, "shikimori:detail": 5000},
    "splits": {"train": 11111, "val": 617, "test": 617},
    "entities": {"characters": 100000, "staff": 200000, "episodes": 50000,
                 "relationships": 20000, "alt_titles": 150000,
                 "descriptions": 20000, "qa_pairs": 300000,
                 "instructions": 100000, "rag_chunks": 90000,
                 "license_tiers": 12345, "franchises": 8000, "franchise_rows": 12345,
                 "studios": 2400, "genres": 42, "themes": 400},
    "field_coverage": {k: {"anime": 100, "share": 0.5} for k in
                       ("year", "episodes (count)", "studios",
                        "genres", "characters", "voice actors",
                        "staff credits", "relationships")},
    "episode_list_share": 0.25,
}


def test_sync_docs_blocks_render_from_summary():
    import sync_docs
    readme = sync_docs.build_block(SUMMARY, "readme")
    card = sync_docs.build_block(SUMMARY, "card")
    training = sync_docs.build_block(SUMMARY, "training")
    assert "12,345" in readme and "50%" in readme
    assert "300,000 / 100,000 / 90,000" in card
    assert "`exports/qa.jsonl` | 300,000" in training
    # Every block must be valid markdown table rows: same pipe count per line.
    for line in readme.splitlines():
        if line.startswith("|"):
            assert line.count("|") == line.count("|")
    assert sync_docs.replace_block("a\n" + sync_docs.START + "\nx\n" + sync_docs.END + "\nb",
                                   "BODY").count("BODY") == 1


def test_sync_docs_tokens_render_and_reject_unknown_metrics():
    import pytest
    import sync_docs
    lookup = sync_docs.metrics(SUMMARY)
    out = sync_docs.render_tokens("v{{v:version}} n{{n:qa_pairs}}", lookup)
    assert out == "v9.9.9 n300,000"
    with pytest.raises(SystemExit):
        sync_docs.render_tokens("{{n:not_a_metric}}", lookup)


def test_cli_help_lists_every_command():
    from src.cli import COMMANDS, HELP, main
    assert main(["--help"]) == 0
    assert main([]) == 2
    for command in COMMANDS:
        assert command in HELP
