from datetime import datetime
from datetime import timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.rate_providers.crypto.client import CryptoRateClient
from tests.rate_providers.conftest import mock_http_client


class TestCryptoRateClient:
    async def test_get_current_parses_rate_from_response(self):
        # _resolve_id and get_current both do `import httpx` in the same module
        # here, so both AsyncClient() calls share one patch target — side_effect
        # stands in for each call in order: id resolution first, then the rate fetch.
        ids_client = mock_http_client([{"id": "bitcoin", "symbol": "btc"}])
        rate_client = mock_http_client({"bitcoin": {"uah": 3249577}})
        with patch("httpx.AsyncClient", side_effect=[ids_client, rate_client]):
            result = await CryptoRateClient().get_current(
                currency_ticker="BTC", base_currency_ticker="UAH"
            )

        assert result == Decimal("3249577")
        url, kwargs = rate_client.get.await_args.args[0], rate_client.get.await_args.kwargs
        assert url == "https://api.coingecko.com/api/v3/simple/price"
        assert kwargs["params"] == {"ids": "bitcoin", "vs_currencies": "uah"}

    async def test_get_historical_parses_nested_market_data(self):
        ids_client = mock_http_client([{"id": "bitcoin", "symbol": "btc"}])
        rate_client = mock_http_client({"market_data": {"current_price": {"uah": 3200000}}})
        with patch("httpx.AsyncClient", side_effect=[ids_client, rate_client]):
            result = await CryptoRateClient().get_historical(
                currency_ticker="BTC",
                base_currency_ticker="UAH",
                rate_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            )

        assert result == Decimal("3200000")
        url, kwargs = rate_client.get.await_args.args[0], rate_client.get.await_args.kwargs
        assert url == "https://api.coingecko.com/api/v3/coins/bitcoin/history"
        assert kwargs["params"] == {"date": "15-08-2026"}

    async def test_raises_when_ticker_has_no_matching_coin(self):
        ids_client = mock_http_client([])
        with patch("httpx.AsyncClient", return_value=ids_client):
            with pytest.raises(NotFoundError):
                await CryptoRateClient().get_current(
                    currency_ticker="DOGE", base_currency_ticker="USD"
                )

    async def test_ticker_exists_true_when_coin_resolves(self):
        client = mock_http_client([{"id": "bitcoin", "symbol": "btc"}])
        with patch("httpx.AsyncClient", return_value=client):
            assert await CryptoRateClient().ticker_exists(currency_ticker="BTC") is True

    async def test_ticker_exists_false_when_no_coin_matches(self):
        client = mock_http_client([])
        with patch("httpx.AsyncClient", return_value=client):
            assert await CryptoRateClient().ticker_exists(currency_ticker="ZZZ") is False


class TestCryptoRateClientResolveId:
    async def test_resolves_ticker_via_coingecko_markets(self):
        client = mock_http_client([{"id": "bitcoin", "symbol": "btc", "market_cap_rank": 1}])
        with patch("httpx.AsyncClient", return_value=client):
            result = await CryptoRateClient()._resolve_id("BTC")

        assert result == "bitcoin"
        url, kwargs = client.get.await_args.args[0], client.get.await_args.kwargs
        assert url == "https://api.coingecko.com/api/v3/coins/markets"
        assert kwargs["params"] == {
            "vs_currency": "usd",
            "symbols": "btc",
            "order": "market_cap_desc",
        }

    async def test_caches_result_and_does_not_refetch(self):
        client = mock_http_client([{"id": "bitcoin", "symbol": "btc"}])
        rate_client = CryptoRateClient()
        with patch("httpx.AsyncClient", return_value=client):
            first = await rate_client._resolve_id("BTC")
            second = await rate_client._resolve_id("btc")  # different case, same cache key

        assert first == second == "bitcoin"
        client.get.assert_awaited_once()

    async def test_cache_is_not_shared_across_instances(self):
        client = mock_http_client([{"id": "bitcoin", "symbol": "btc"}])
        with patch("httpx.AsyncClient", return_value=client):
            await CryptoRateClient()._resolve_id("BTC")
            await CryptoRateClient()._resolve_id("BTC")

        assert client.get.await_count == 2

    async def test_raises_when_no_matching_coin_has_market_data(self):
        client = mock_http_client([])
        with patch("httpx.AsyncClient", return_value=client):
            with pytest.raises(NotFoundError) as exc_info:
                await CryptoRateClient()._resolve_id("DOGE")

        assert exc_info.value.message == Messages.COINGECKO_ID_NOT_FOUND
