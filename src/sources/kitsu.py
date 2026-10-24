from .base import HttpSource


class Kitsu(HttpSource):
    name = "kitsu"

    def __init__(self, cfg: dict, cache_root, per_second: float = 4):
        super().__init__(cfg, cache_root, per_second=per_second)
        self.base = cfg.get("url", "https://kitsu.io/api/edge")
        self.headers = {"Accept": "application/vnd.api+json"}

    def list_page(self, offset: int = 0, limit: int = 500) -> list[dict]:
        data = self.get_json(
            f"{self.base}/anime",
            params={"page[limit]": limit, "page[offset]": offset},
            headers=self.headers,
        )
        return data.get("data", [])

    def total_anime(self) -> int | None:
        data = self.get_json(f"{self.base}/anime", params={"page[limit]": 1}, headers=self.headers)
        return data.get("meta", {}).get("count")

    def detail(self, anime_id: int) -> dict:
        data = self.get_json(f"{self.base}/anime/{anime_id}", headers=self.headers)
        return data.get("data", {})

    def mappings(self, site: str, offset: int = 0, limit: int = 500) -> list[dict]:
        data = self.get_json(
            f"{self.base}/mappings",
            params={"filter[externalSite]": site, "page[limit]": limit, "page[offset]": offset},
            headers=self.headers,
        )
        return data.get("data", [])

    def episodes(self, media_id: int, offset: int = 0, limit: int = 500) -> list[dict]:
        data = self.get_json(
            f"{self.base}/episodes",
            params={"filter[mediaId]": media_id,
                    "page[limit]": limit, "page[offset]": offset},
            headers=self.headers,
        )
        return data.get("data", [])

    def episodes_bulk(self, offset: int = 0, limit: int = 500) -> list[dict]:
        data = self.get_json(
            f"{self.base}/episodes",
            params={"page[limit]": limit, "page[offset]": offset},
            headers=self.headers,
        )
        return data.get("data", [])

    def episodes_with_media(self, offset: int = 0, limit: int = 20) -> tuple[list[dict], list[dict]]:
        data = self.get_json(
            f"{self.base}/episodes",
            params={"include": "media", "page[limit]": limit, "page[offset]": offset},
            headers=self.headers,
        )
        return data.get("data", []), data.get("included", [])

    def episodes_all(self, offset: int = 0, limit: int = 500) -> list[dict]:
        data = self.get_json(
            f"{self.base}/episodes",
            params={"include": "media", "page[limit]": limit, "page[offset]": offset},
            headers=self.headers,
        )
        return data.get("data", [])

    def characters_bulk(self, offset: int = 0, limit: int = 500) -> list[dict]:
        data = self.get_json(
            f"{self.base}/characters",
            params={"page[limit]": limit, "page[offset]": offset},
            headers=self.headers,
        )
        return data.get("data", [])
