from .base import HttpSource


class Shikimori(HttpSource):
    name = "shikimori"

    def __init__(self, cfg: dict, cache_root, per_second: float = 4):
        super().__init__(cfg, cache_root, per_second=per_second)
        self.base = cfg.get("url", "https://shikimori.io/api")

    def list_page(self, page: int = 1, limit: int = 50, order: str = "id") -> list[dict]:
        return self.get_json(f"{self.base}/animes",
                             params={"page": page, "limit": limit, "order": order})

    def detail(self, anime_id: int) -> dict:
        return self.get_json(f"{self.base}/animes/{anime_id}")

    def roles(self, anime_id: int) -> list[dict]:
        return self.get_json(f"{self.base}/animes/{anime_id}/roles")

    def related(self, anime_id: int) -> list[dict]:
        return self.get_json(f"{self.base}/animes/{anime_id}/related")

    def genres(self) -> list[dict]:
        return self.get_json(f"{self.base}/genres")

    def studios(self) -> list[dict]:
        return self.get_json(f"{self.base}/studios")
