import time


class RateLimiter:
    def __init__(self, per_second: float = 0.0, per_minute: float = 0.0):
        interval = 0.0
        if per_minute:
            interval = max(interval, 60.0 / per_minute)
        if per_second:
            interval = max(interval, 1.0 / per_second)
        self.min_interval = interval
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delta = self._last + self.min_interval - now
        if delta > 0:
            time.sleep(delta)
        self._last = time.monotonic()

    def backoff(self, seconds: float) -> None:
        time.sleep(seconds)
