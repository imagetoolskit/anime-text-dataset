from .base import HttpSource

LIGHT_QUERY = """
query ($ids: [Int]) {
  Page(page: 1, perPage: 50) {
    media(id_in: $ids, type: ANIME) {
      id
      idMal
      format
      status
      season
      seasonYear
      episodes
      duration
      startDate { year month day }
      endDate { year month day }
      averageScore
      popularity
      favourites
      title { romaji english native }
      genres
    }
  }
}
"""

FULL_QUERY = """
query ($ids: [Int]) {
  Page(page: 1, perPage: 15) {
    media(id_in: $ids, type: ANIME) {
      id
      idMal
      format
      status
      source
      countryOfOrigin
      season
      seasonYear
      episodes
      duration
      isAdult
      startDate { year month day }
      endDate { year month day }
      averageScore
      meanScore
      popularity
      favourites
      description(asHtml: false)
      title { romaji english native }
      synonyms
      genres
      tags { name description rank }
      externalLinks { site url type }
      studios {
        edges { isMain node { id name isAnimationStudio } }
      }
      characters(page: 1, perPage: 15) {
        pageInfo { total }
        edges {
          role
          node { id name { full native } description gender age }
          voiceActors(language: JAPANESE) { id name { native full } }
        }
      }
      staff(page: 1, perPage: 15) {
        pageInfo { total }
        edges { role node { id name { native full } } }
      }
      relations {
        edges {
          relationType
          node { ... on Media { id type format status title { romaji } startDate { year } } }
        }
      }
    }
  }
}
"""


class AniList(HttpSource):
    name = "anilist"

    def __init__(self, cfg: dict, cache_root, per_minute: float = 28):
        super().__init__(cfg, cache_root, per_minute=per_minute)
        self.url = cfg.get("url", "https://graphql.anilist.co")

    def _post(self, query: str, variables: dict):
        payload = {"query": query, "variables": variables}
        key = "POST|" + query + "|" + str(sorted(variables.items()))
        import hashlib
        import json
        import pathlib

        cache_path = self._cache_path(hashlib.sha256(key.encode()).hexdigest())
        if cache_path.exists():
            cached = self._cache_read(cache_path)
            if cached is not None:
                self.stats["cache_hits"] += 1
                return cached
        import requests

        last_err = None
        for attempt in range(6):
            self.limiter.wait()
            self.stats["requests"] += 1
            try:
                resp = self.session.post(self.url, json=payload, timeout=90)
            except requests.RequestException as exc:
                last_err = exc
                self.stats["errors"] += 1
                self.limiter.backoff(min(60, 2 ** attempt))
                continue
            if resp.status_code == 200:
                data = resp.json()
                if data.get("errors"):
                    raise RuntimeError(f"anilist graphql errors: {data['errors']}")
                body = data.get("data", {})
                cache_path.write_text(json.dumps({"status": 200, "body": body}, ensure_ascii=False),
                                      encoding="utf-8")
                return body
            if resp.status_code in (403, 429, 500, 502, 503, 504):
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else min(120, 5 * (2 ** attempt))
                except ValueError:
                    wait = min(120, 5 * (2 ** attempt))
                self.limiter.backoff(wait)
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                continue
            raise RuntimeError(f"anilist: HTTP {resp.status_code}: {resp.text[:200]}")
        raise RuntimeError(f"anilist: retries exhausted: {last_err}")

    def light(self, ids: list[int]) -> list[dict]:
        body = self._post(LIGHT_QUERY, {"ids": ids})
        return body.get("Page", {}).get("media") or []

    def full(self, ids: list[int]) -> list[dict]:
        body = self._post(FULL_QUERY, {"ids": ids})
        return body.get("Page", {}).get("media") or []
