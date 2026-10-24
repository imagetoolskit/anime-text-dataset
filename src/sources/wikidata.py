from .base import HttpSource

ANIME_QUERY = """
SELECT ?item ?itemLabel ?enLabel ?enDescription ?malId ?annId ?startDate WHERE {
  ?item wdt:P31/wdt:P279* wd:Q1107 .
  OPTIONAL { ?item wdt:P4086 ?malId }
  OPTIONAL { ?item wdt:P1243 ?annId }
  OPTIONAL { ?item wdt:P577 ?startDate }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja". }
}
ORDER BY ?item
"""

PROBE_QUERY = """
SELECT ?p ?pLabel WHERE {
  ?p a wikibase:Property ; rdfs:label ?l .
  FILTER(LANG(?l) = "en" && (CONTAINS(LCASE(?l), "myanimelist") || CONTAINS(LCASE(?l), "anime news network")))
}
"""


class Wikidata(HttpSource):
    name = "wikidata"

    def __init__(self, cfg: dict, cache_root, per_second: float = 1):
        super().__init__(cfg, cache_root, per_second=per_second)
        self.url = cfg.get("url", "https://query.wikidata.org/sparql")
        self.headers = {"Accept": "application/sparql-results+json",
                        "User-Agent": "anime-text-dataset/0.1 (research)"}

    def sparql(self, query: str) -> dict:
        return self.get_json(self.url, params={"query": query, "format": "json"},
                             headers=self.headers, timeout=120)

    def probe_properties(self) -> dict:
        data = self.sparql(PROBE_QUERY)
        out = {}
        for b in data.get("results", {}).get("bindings", []):
            key = b.get("pLabel", {}).get("value") or b["p"]["value"].rsplit("/", 1)[-1]
            out[key] = b["p"]["value"].rsplit("/", 1)[-1]
        return out

    def fetch_anime_items(self, limit: int = 20000, batch: int = 5000) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        while offset < limit:
            q = ANIME_QUERY.rstrip() + f"\nLIMIT {batch} OFFSET {offset}"
            data = self.sparql(q)
            batch_rows = data.get("results", {}).get("bindings", [])
            rows.extend(batch_rows)
            if len(batch_rows) < batch:
                break
            offset += batch
        return rows
