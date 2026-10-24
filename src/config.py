import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Single source of truth for the release version. Bumped in one place only;
# the docs, the site pages and reports/summary.json all read it from here.
VERSION = "2.0.0"


def load(name: str = "config.json") -> dict:
    with open(ROOT / "config" / name, encoding="utf-8") as f:
        return json.load(f)
