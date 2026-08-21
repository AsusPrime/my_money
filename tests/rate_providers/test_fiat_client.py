from datetime import datetime
from datetime import timezone
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from src.rate_providers.fiat.client import FiatRateClient
from tests.rate_providers.conftest import mock_http_client


class TestFiatRateClient:
    async def test_get_current_parses_rate_from_response(self):
        client = mock_http_client({"rates": {"USD": 1.08}})
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            result = await FiatRateClient().get_current(
                currency_ticker="EUR", base_currency_ticker="USD"
            )

        assert result == Decimal("1.08")
        url, kwargs = client.get.await_args.args[0], client.get.await_args.kwargs
        assert url == "https://api.frankfurter.dev/v1/latest"
        assert kwargs["params"] == {"from": "EUR", "to": "USD"}

    async def test_get_historical_requests_the_given_date(self):
        client = mock_http_client({"rates": {"USD": 1.05}})
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            result = await FiatRateClient().get_historical(
                currency_ticker="EUR",
                base_currency_ticker="USD",
                rate_at=datetime(2026, 8, 15, 14, 30, tzinfo=timezone.utc),
            )

        assert result == Decimal("1.05")
        url = client.get.await_args.args[0]
        assert url == "https://api.frankfurter.dev/v1/2026-08-15"

    async def test_raises_on_non_2xx_response(self):
        client = mock_http_client({"rates": {}})
        client.get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom", request=MagicMock(), response=MagicMock()
        )
        with patch("src.rate_providers.fiat.client.httpx.AsyncClient", return_value=client):
            with pytest.raises(httpx.HTTPStatusError):
                await FiatRateClient().get_current(
                    currency_ticker="EUR", base_currency_ticker="USD"
                )
