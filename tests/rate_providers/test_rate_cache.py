from decimal import Decimal
from unittest.mock import patch

from src.rate_providers.rate_cache import RateCache


class TestRateCache:
    def test_returns_none_when_nothing_cached(self):
        cache = RateCache(ttl_seconds=60)

        assert cache.get("EUR", "USD") is None

    def test_returns_the_cached_rate_before_ttl_expires(self):
        cache = RateCache(ttl_seconds=60)
        with patch("src.rate_providers.rate_cache.time.monotonic", return_value=1000.0):
            cache.set("EUR", "USD", Decimal("1.08"))

        with patch("src.rate_providers.rate_cache.time.monotonic", return_value=1059.0):
            assert cache.get("EUR", "USD") == Decimal("1.08")

    def test_expires_the_cached_rate_after_ttl(self):
        cache = RateCache(ttl_seconds=60)
        with patch("src.rate_providers.rate_cache.time.monotonic", return_value=1000.0):
            cache.set("EUR", "USD", Decimal("1.08"))

        with patch("src.rate_providers.rate_cache.time.monotonic", return_value=1060.0):
            assert cache.get("EUR", "USD") is None

    def test_different_currency_pairs_do_not_collide(self):
        cache = RateCache(ttl_seconds=60)
        cache.set("EUR", "USD", Decimal("1.08"))
        cache.set("EUR", "UAH", Decimal("43.5"))

        assert cache.get("EUR", "USD") == Decimal("1.08")
        assert cache.get("EUR", "UAH") == Decimal("43.5")
        assert cache.get("USD", "EUR") is None
