import time
from decimal import Decimal


class RateCache:
    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._store: dict[tuple[str, str], tuple[Decimal, float]] = {}

    def get(self, currency_ticker: str, base_currency_ticker: str) -> Decimal | None:
        cached = self._store.get((currency_ticker, base_currency_ticker))
        if cached is None:
            return None

        rate, cached_at = cached
        if time.monotonic() - cached_at >= self._ttl_seconds:
            return None

        return rate

    def set(self, currency_ticker: str, base_currency_ticker: str, rate: Decimal) -> None:
        self._store[(currency_ticker, base_currency_ticker)] = (rate, time.monotonic())
