from datetime import datetime
from datetime import timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import patch

from src.core.exceptions.exceptions import NotFoundError
from src.enums.enums import CurrencyTypeEnum
from src.services.exchange_rate_service import ExchangeRateService


class TestExchangeRateService:
    """ExchangeRateService itself holds no provider logic — it just resolves a
    client via rate_providers.registry.get_rate_client and delegates. Provider
    behavior is tested under tests/rate_providers/."""

    async def test_get_historical_rate_delegates_to_resolved_client(self):
        client = AsyncMock()
        client.get_historical.return_value = Decimal("1.08")
        with patch(
            "src.services.exchange_rate_service.get_rate_client", return_value=client
        ) as get_client:
            result = await ExchangeRateService.get_historical_rate(
                currency_ticker="EUR",
                base_currency_ticker="USD",
                currency_type=CurrencyTypeEnum.FIAT,
                rate_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            )

        get_client.assert_called_once_with(CurrencyTypeEnum.FIAT)
        client.get_historical.assert_awaited_once_with(
            currency_ticker="EUR",
            base_currency_ticker="USD",
            rate_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        )
        assert result == Decimal("1.08")

    async def test_get_current_rate_delegates_to_resolved_client(self):
        client = AsyncMock()
        client.get_current.return_value = Decimal("65000")
        with patch(
            "src.services.exchange_rate_service.get_rate_client", return_value=client
        ) as get_client:
            result = await ExchangeRateService.get_current_rate(
                currency_ticker="BTC",
                base_currency_ticker="USD",
                currency_type=CurrencyTypeEnum.CRYPTO,
            )

        get_client.assert_called_once_with(CurrencyTypeEnum.CRYPTO)
        client.get_current.assert_awaited_once_with(
            currency_ticker="BTC", base_currency_ticker="USD"
        )
        assert result == Decimal("65000")

    async def test_ticker_exists_delegates_to_resolved_client(self):
        client = AsyncMock()
        client.ticker_exists.return_value = True
        with patch(
            "src.services.exchange_rate_service.get_rate_client", return_value=client
        ) as get_client:
            result = await ExchangeRateService.ticker_exists(
                currency_ticker="EUR", currency_type=CurrencyTypeEnum.FIAT
            )

        get_client.assert_called_once_with(CurrencyTypeEnum.FIAT)
        client.ticker_exists.assert_awaited_once_with(currency_ticker="EUR")
        assert result is True

    async def test_ticker_exists_false_when_no_client_configured_for_type(self):
        # bond/other have no rate client at all — nothing to validate against,
        # fail closed rather than trust blindly
        with patch(
            "src.services.exchange_rate_service.get_rate_client",
            side_effect=NotFoundError("no client"),
        ):
            result = await ExchangeRateService.ticker_exists(
                currency_ticker="XYZ", currency_type=CurrencyTypeEnum.BOND
            )

        assert result is False
