import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Single source of truth for the release version. Bumped in one place only;
# the docs, the site pages and reports/summary.json all read it from here.
VERSION = "2.0.0"

# Environment overrides documented in config/.env.example. Values are coerced
# to the type of the JSON value they replace, so `ATDS_SHIKIMORI_RPS=2.5`
# stays a float and `ATDS_SEED=7` stays an int.
ENV_OVERRIDES = {
    "ATDS_SEED": ("seed",),
    "ATDS_MIN_ANIME": ("min_anime_titles",),
    "ATDS_TARGET_ANIME": ("target_anime_titles",),
    "ATDS_MAX_RUNTIME_HOURS": ("max_runtime_hours",),
    "ATDS_MAX_RUNTIME_ANILIST": ("max_source_runtime_hours", "anilist"),
    "ATDS_MAX_RUNTIME_KITSU": ("max_source_runtime_hours", "kitsu"),
    "ATDS_MAX_RUNTIME_SHIKIMORI": ("max_source_runtime_hours", "shikimori"),
    "ATDS_MAX_RUNTIME_WIKIDATA": ("max_source_runtime_hours", "wikidata"),
    "ATDS_MAX_RUNTIME_ANN": ("max_source_runtime_hours", "ann"),
    "ATDS_CHECKPOINT_INTERVAL": ("checkpoint_interval",),
    "ATDS_ANILIST_RPM": ("anilist", "per_minute"),
    "ATDS_KITSU_RPS": ("kitsu", "per_second"),
    "ATDS_SHIKIMORI_RPS": ("shikimori", "per_second"),
    "ATDS_WIKIDATA_RPS": ("wikidata", "per_second"),
    "ATDS_ANN_RPS": ("ann", "per_second"),
}


def _coerce(value: str, template):
    """Cast an env string to the type of the JSON value it overrides."""
    if isinstance(template, bool):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _load_dotenv(path: pathlib.Path) -> None:
    """Read KEY=VALUE pairs from `.env` without overriding real env vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _apply_env(cfg: dict) -> dict:
    for env_name, path in ENV_OVERRIDES.items():
        if env_name not in os.environ:
            continue
        node = cfg
        for key in path[:-1]:
            node = node.setdefault(key, {})
        node[path[-1]] = _coerce(os.environ[env_name], node.get(path[-1]))
    return cfg


def load(name: str = "config.json") -> dict:
    _load_dotenv(ROOT / ".env")
    with open(ROOT / "config" / name, encoding="utf-8") as f:
        return _apply_env(json.load(f))
