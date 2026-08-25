from decimal import Decimal
from unittest.mock import AsyncMock

from src.services.currency_conversion import convert_amounts_to_total
from tests.services.conftest import make_currency_row


class TestConvertAmountsToTotal:
    async def test_returns_zero_for_empty_amounts(self, uow):
        result = await convert_amounts_to_total(uow=uow, amounts={}, base_currency_ticker="UAH")

        assert result == Decimal("0")

    async def test_sums_base_currency_amounts_directly(self, uow):
        result = await convert_amounts_to_total(
            uow=uow,
            amounts={"UAH": Decimal("100")},
            base_currency_ticker="UAH",
        )

        # no currency/rate lookup needed — same-as-base amounts pass through
        assert result == Decimal("100")
        uow.currencies.find_one_or_none.assert_not_called()

    async def test_converts_a_foreign_currency_using_the_current_rate(self, uow):
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="EUR")
        exchange_rate_service = AsyncMock()
        exchange_rate_service.get_current_rate.return_value = Decimal("45")

        result = await convert_amounts_to_total(
            uow=uow,
            amounts={"EUR": Decimal("100")},
            base_currency_ticker="UAH",
            exchange_rate_service=exchange_rate_service,
        )

        assert result == Decimal("4500")
        exchange_rate_service.get_current_rate.assert_awaited_once_with(
            currency_ticker="EUR", base_currency_ticker="UAH", currency_type="fiat"
        )

    async def test_sums_base_and_multiple_foreign_currencies_together(self, uow):
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        exchange_rate_service = AsyncMock()
        exchange_rate_service.get_current_rate.return_value = Decimal("41")

        result = await convert_amounts_to_total(
            uow=uow,
            amounts={"UAH": Decimal("100"), "USD": Decimal("10")},
            base_currency_ticker="UAH",
            exchange_rate_service=exchange_rate_service,
        )

        assert result == Decimal("510")
