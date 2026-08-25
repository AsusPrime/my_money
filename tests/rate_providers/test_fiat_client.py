from datetime import datetime
from datetime import timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.rate_providers.fiat.client import FiatRateClient
from tests.rate_providers.conftest import mock_http_client

LATEST_PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api/v1/currencies/{currency}.json"
LATEST_FALLBACK = "https://currency-api.pages.dev/v1/currencies/{currency}.json"
HISTORICAL_PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/{currency}.json"
HISTORICAL_FALLBACK = "https://{date}.currency-api.pages.dev/v1/currencies/{currency}.json"


def mock_http_client_sequence(responses):
    """Like mock_http_client, but returns a different canned response for each
    successive client.get() call — for testing host-fallback."""
    client = AsyncMock()
    client.get = AsyncMock(side_effect=responses)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def make_response(json_data=None, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    if status_code >= 400 and status_code != 404:
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "boom", request=MagicMock(), response=MagicMock(status_code=status_code)
            )
        )
    else:
        response.raise_for_status = MagicMock()
    response.json.return_value = json_data
    return response


class TestFiatRateClient:
    async def test_get_current_parses_rate_from_response(self):
        client = mock_http_client({"eur": {"usd": 1.08}})
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            result = await FiatRateClient().get_current(
                currency_ticker="EUR", base_currency_ticker="USD"
            )

        assert result == Decimal("1.08")
        url = client.get.await_args.args[0]
        # no "@latest" — omitting the version entirely is the dataset's HEAD,
        # verified live on both hosts
        assert url == LATEST_PRIMARY.format(currency="eur")

    async def test_get_historical_requests_the_given_date(self):
        client = mock_http_client({"eur": {"usd": 1.05}})
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            result = await FiatRateClient().get_historical(
                currency_ticker="EUR",
                base_currency_ticker="USD",
                rate_at=datetime(2026, 8, 15, 14, 30, tzinfo=timezone.utc),
            )

        assert result == Decimal("1.05")
        url = client.get.await_args.args[0]
        assert url == HISTORICAL_PRIMARY.format(date="2026-08-15", currency="eur")

    async def test_falls_back_to_second_host_on_a_transient_error(self):
        # jsDelivr erroring shouldn't be fatal — the project's own docs
        # recommend falling back to the Cloudflare Pages mirror
        responses = [make_response(status_code=500), make_response({"eur": {"usd": 1.1}})]
        client = mock_http_client_sequence(responses)
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            result = await FiatRateClient().get_current(
                currency_ticker="EUR", base_currency_ticker="USD"
            )

        assert result == Decimal("1.1")
        assert client.get.await_count == 2
        first_url = client.get.await_args_list[0].args[0]
        second_url = client.get.await_args_list[1].args[0]
        assert first_url == LATEST_PRIMARY.format(currency="eur")
        assert second_url == LATEST_FALLBACK.format(currency="eur")

    async def test_raises_when_both_hosts_fail(self):
        client = mock_http_client_sequence(
            [make_response(status_code=500), make_response(status_code=500)]
        )
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            with pytest.raises(httpx.HTTPStatusError):
                await FiatRateClient().get_current(
                    currency_ticker="EUR", base_currency_ticker="USD"
                )

        assert client.get.await_count == 2

    async def test_raises_not_found_when_the_currency_is_missing_from_the_dataset(self):
        # a KeyError (currency not tracked at all) is a different, permanent
        # problem from a date-coverage gap, and must say so, not "for this date"
        client = mock_http_client({"eur": {}})
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            with pytest.raises(NotFoundError) as exc_info:
                await FiatRateClient().get_current(
                    currency_ticker="EUR", base_currency_ticker="ZZZ"
                )

        assert exc_info.value.message == Messages.RATE_CURRENCY_NOT_SUPPORTED

    async def test_get_historical_raises_not_found_when_the_date_is_out_of_coverage(self):
        # a 404 here means the date is outside the dataset's coverage window
        # (currently starts ~2024) — every day *within* coverage has a
        # snapshot (verified live, including weekends/holidays), so there's
        # no "nearby" date worth retrying
        client = mock_http_client_sequence([make_response(status_code=404)])
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            with pytest.raises(NotFoundError) as exc_info:
                await FiatRateClient().get_historical(
                    currency_ticker="EUR",
                    base_currency_ticker="UAH",
                    rate_at=datetime(2015, 1, 1, 10, 0, tzinfo=timezone.utc),
                )

        assert exc_info.value.message == Messages.RATE_NOT_AVAILABLE_FOR_DATE
        assert client.get.await_count == 1

    async def test_get_historical_falls_back_to_second_host_on_a_transient_error(self):
        responses = [make_response(status_code=500), make_response({"eur": {"uah": 43.5}})]
        client = mock_http_client_sequence(responses)
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            result = await FiatRateClient().get_historical(
                currency_ticker="EUR",
                base_currency_ticker="UAH",
                rate_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            )

        assert result == Decimal("43.5")
        assert client.get.await_count == 2
        first_url = client.get.await_args_list[0].args[0]
        second_url = client.get.await_args_list[1].args[0]
        assert first_url == HISTORICAL_PRIMARY.format(date="2025-01-01", currency="eur")
        assert second_url == HISTORICAL_FALLBACK.format(date="2025-01-01", currency="eur")

    async def test_ticker_exists_true_for_known_iso_code(self):
        assert await FiatRateClient().ticker_exists(currency_ticker="EUR") is True

    async def test_ticker_exists_is_case_insensitive(self):
        assert await FiatRateClient().ticker_exists(currency_ticker="eur") is True

    async def test_ticker_exists_false_for_unknown_code(self):
        assert await FiatRateClient().ticker_exists(currency_ticker="ZZZ") is False

    async def test_caches_current_rate_and_does_not_refetch_within_ttl(self):
        client = mock_http_client({"eur": {"usd": 1.08}})
        rate_client = FiatRateClient()
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            first = await rate_client.get_current(
                currency_ticker="EUR", base_currency_ticker="USD"
            )
            second = await rate_client.get_current(
                currency_ticker="EUR", base_currency_ticker="USD"
            )

        assert first == second == Decimal("1.08")
        client.get.assert_awaited_once()

    async def test_get_historical_is_never_cached(self):
        # a ledger entry needs the actual rate at its specific past date, not
        # a cached "current" approximation, so get_historical never caches
        client = mock_http_client({"eur": {"usd": 1.05}})
        rate_client = FiatRateClient()
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            await rate_client.get_historical(
                currency_ticker="EUR",
                base_currency_ticker="USD",
                rate_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            )
            await rate_client.get_historical(
                currency_ticker="EUR",
                base_currency_ticker="USD",
                rate_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            )

        assert client.get.await_count == 2

    async def test_rate_cache_is_not_shared_across_instances(self):
        client = mock_http_client({"eur": {"usd": 1.08}})
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            await FiatRateClient().get_current(currency_ticker="EUR", base_currency_ticker="USD")

        client_2 = mock_http_client({"eur": {"usd": 1.08}})
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client_2):
            await FiatRateClient().get_current(currency_ticker="EUR", base_currency_ticker="USD")

        client_2.get.assert_awaited_once()
