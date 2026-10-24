import html
import re
import sys

from .base import HttpSource

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
KIND_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
INFO_RE = re.compile(
    r"<div class=\"wiki-info\">(.*?)</div>\s*</div>", re.S
)
TAG_RE = re.compile(r"<[^>]+>")


def _clean(fragment: str) -> str:
    text = TAG_RE.sub(" ", fragment)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


class ANN(HttpSource):
    name = "ann"

    def __init__(self, cfg: dict, cache_root, per_second: float = 1.5):
        super().__init__(cfg, cache_root, per_second=per_second)
        self.base = cfg.get("base", "https://www.animenewsnetwork.com/encyclopedia/anime.php")

    def fetch(self, anime_id: int) -> dict | None:
        try:
            page = self.get_text(f"{self.base}?id={anime_id}")
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise
        title_m = TITLE_RE.search(page)
        if not title_m:
            return None
        title = _clean(title_m.group(1))
        if title.lower().startswith("anime news network"):
            return None
        kind_m = KIND_RE.search(page)
        kind = _clean(kind_m.group(1)) if kind_m else ""
        is_manga = "manga" in kind.lower() and "(tv)" not in kind.lower()
        if is_manga:
            return None
        return {"id": anime_id, "title": title, "kind": kind, "is_anime": not is_manga}
