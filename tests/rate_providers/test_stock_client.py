from datetime import datetime
from datetime import timezone

import pytest

from src.rate_providers.stock.client import StockRateClient


class TestStockRateClientStub:
    """Twelve Data requires an API key even on its free tier, which isn't set up
    yet — both methods are still unimplemented stubs. Delete/replace with
    HTTP-mocked tests (same pattern as test_fiat_client.py /
    test_crypto_client.py) once a key is configured and this is wired up."""

    async def test_get_current_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await StockRateClient().get_current(
                currency_ticker="AAPL", base_currency_ticker="USD"
            )

    async def test_get_historical_not_implemented(self):
        with pytest.raises(NotImplementedError):
            await StockRateClient().get_historical(
                currency_ticker="AAPL",
                base_currency_ticker="USD",
                rate_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            )


class TestStockRateClientTickerExists:
    """Nothing to validate against yet — fails closed (rejects) rather than
    trusting an unverifiable ticker, until Twelve Data is wired up."""

    async def test_always_returns_false(self):
        assert await StockRateClient().ticker_exists(currency_ticker="AAPL") is False
