import hashlib
import json
import pathlib
import time

import requests

from ..config import VERSION
from ..ratelimit import RateLimiter


class HttpSource:
    name = "base"

    def __init__(self, cfg: dict, cache_root: pathlib.Path, per_minute: float = 0.0, per_second: float = 0.0):
        self.cfg = cfg
        self.cache_dir = pathlib.Path(cache_root) / self.name
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.limiter = RateLimiter(per_second=per_second, per_minute=per_minute)
        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            f"anime-text-dataset/{VERSION} (+https://animearray.site; contact muqeet@animearray.site; "
            "research collection, respects rate limits)"
        )
        self.stats = {"requests": 0, "cache_hits": 0, "errors": 0}
        self._started = time.time()

    def _cache_path(self, key: str) -> pathlib.Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _cache_read(self, path: pathlib.Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("status") in (200, 201):
                return data.get("body")
        except Exception:
            return None
        return None

    def get_json(self, url: str, params: dict | None = None, headers: dict | None = None,
                 use_cache: bool = True, timeout: int = 60, max_retries: int = 6):
        key = url + "|" + json.dumps(params or {}, sort_keys=True, ensure_ascii=True)
        cache_path = self._cache_path(key)
        if use_cache and cache_path.exists():
            cached = self._cache_read(cache_path)
            if cached is not None:
                self.stats["cache_hits"] += 1
                return cached
        last_err = None
        for attempt in range(max_retries):
            self.limiter.wait()
            self.stats["requests"] += 1
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=timeout)
            except requests.RequestException as exc:
                last_err = exc
                self.stats["errors"] += 1
                self.limiter.backoff(min(60, 2 ** attempt))
                continue
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except ValueError as exc:
                    last_err = exc
                    self.limiter.backoff(min(60, 2 ** attempt))
                    continue
                cache_path.write_text(
                    json.dumps({"status": 200, "body": body}, ensure_ascii=False), encoding="utf-8"
                )
                return body
            if resp.status_code in (403, 429, 500, 502, 503, 504):
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else min(120, 3 * (2 ** attempt))
                except ValueError:
                    wait = min(120, 3 * (2 ** attempt))
                self.limiter.backoff(wait)
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                continue
            self.stats["errors"] += 1
            raise RuntimeError(f"{self.name}: HTTP {resp.status_code} for {url} params={params}")
        raise RuntimeError(f"{self.name}: retries exhausted for {url}: {last_err}")

    def get_text(self, url: str, use_cache: bool = True, timeout: int = 60, max_retries: int = 4) -> str:
        key = "TEXT|" + url
        cache_path = self._cache_path(key)
        if use_cache and cache_path.exists():
            cached = self._cache_read(cache_path)
            if cached is not None:
                self.stats["cache_hits"] += 1
                return cached
        last_err = None
        for attempt in range(max_retries):
            self.limiter.wait()
            self.stats["requests"] += 1
            try:
                resp = self.session.get(url, timeout=timeout)
            except requests.RequestException as exc:
                last_err = exc
                self.stats["errors"] += 1
                self.limiter.backoff(min(60, 2 ** attempt))
                continue
            if resp.status_code == 200:
                text = resp.text
                cache_path.write_text(
                    json.dumps({"status": 200, "body": text}, ensure_ascii=False), encoding="utf-8"
                )
                return text
            if resp.status_code in (403, 429, 500, 502, 503, 504):
                self.limiter.backoff(min(120, 3 * (2 ** attempt)))
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                continue
            raise RuntimeError(f"{self.name}: HTTP {resp.status_code} for {url}")
        raise RuntimeError(f"{self.name}: retries exhausted for {url}: {last_err}")
