import pytest
from sqlalchemy.exc import IntegrityError

from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import AlreadyExistsError
from src.core.exceptions.exceptions import ConflictError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.schemas.currency import CurrencyCreateSchema
from src.schemas.currency import CurrencyUpdateSchema
from src.services.currency_service import CurrencyService
from tests.services.conftest import make_currency_row


def fk_violation() -> IntegrityError:
    """Simulates the IntegrityError Postgres raises for an `ondelete="RESTRICT"`
    violation — e.g. deleting a Currency that an Account/Ledger row still references."""
    return IntegrityError(
        "DELETE FROM currencies WHERE ticker = :ticker",
        {"ticker": "USD"},
        Exception('update or delete on table "currencies" violates foreign key constraint'),
    )


class TestGetAllCurrencies:
    async def test_returns_all_currencies(self, uow):
        uow.currencies.find_all.return_value = [
            make_currency_row(ticker="USD"),
            make_currency_row(ticker="BTC", name=None, currency_type="crypto"),
        ]

        result = await CurrencyService.get_all_currencies(uow=uow)

        assert [c.ticker for c in result.items] == ["USD", "BTC"]

    async def test_returns_empty_list_when_no_currencies(self, uow):
        uow.currencies.find_all.return_value = []

        result = await CurrencyService.get_all_currencies(uow=uow)

        assert result.items == []


class TestGetCurrencyByTicker:
    async def test_returns_currency_when_found(self, uow):
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")

        result = await CurrencyService.get_currency_by_ticker(uow=uow, ticker="USD")

        assert result.ticker == "USD"

    async def test_raises_not_found_when_missing(self, uow):
        uow.currencies.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await CurrencyService.get_currency_by_ticker(uow=uow, ticker="XXX")

        assert exc_info.value.message == Messages.CURRENCY_NOT_FOUND


class TestCreateCurrency:
    async def test_creates_currency_when_ticker_is_new(self, uow):
        uow.currencies.find_one_or_none.return_value = None
        uow.currencies.add_one.return_value = make_currency_row(ticker="EUR", name="Euro")

        result = await CurrencyService.create_currency(
            uow=uow,
            currency_data=CurrencyCreateSchema(ticker="EUR", name="Euro", currency_type="fiat"),
        )

        assert result.ticker == "EUR"
        uow.currencies.add_one.assert_awaited_once()

    async def test_raises_already_exists_when_ticker_taken(self, uow):
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")

        with pytest.raises(AlreadyExistsError) as exc_info:
            async with uow:
                await CurrencyService.create_currency(
                    uow=uow,
                    currency_data=CurrencyCreateSchema(ticker="USD", name="US Dollar", currency_type="fiat"),
                )

        assert exc_info.value.message == Messages.CURRENCY_ALREADY_EXISTS
        uow.currencies.add_one.assert_not_called()
        assert uow.rolled_back is True

    async def test_raises_add_record_error_when_insert_fails(self, uow):
        uow.currencies.find_one_or_none.return_value = None
        uow.currencies.add_one.return_value = None

        with pytest.raises(AddRecordError) as exc_info:
            await CurrencyService.create_currency(
                uow=uow,
                currency_data=CurrencyCreateSchema(ticker="EUR", name="Euro", currency_type="fiat"),
            )

        assert exc_info.value.message == Messages.ERROR_FILLED_TO_ADD_NEW_CURRENCY


class TestUpdateCurrencyByTicker:
    async def test_updates_currency_when_found(self, uow):
        uow.currencies.edit_one.return_value = make_currency_row(ticker="USD", name="US Dollar Renamed")

        result = await CurrencyService.update_currency_by_ticker(
            uow=uow, ticker="USD", currency_data=CurrencyUpdateSchema(name="US Dollar Renamed")
        )

        assert result.name == "US Dollar Renamed"

    async def test_raises_not_found_when_missing(self, uow):
        uow.currencies.edit_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await CurrencyService.update_currency_by_ticker(
                uow=uow, ticker="XXX", currency_data=CurrencyUpdateSchema(name="Whatever")
            )

        assert exc_info.value.message == Messages.CURRENCY_NOT_FOUND


class TestDeleteCurrencyByTicker:
    async def test_deletes_currency_when_not_referenced(self, uow):
        uow.currencies.delete_one.return_value = make_currency_row(ticker="EUR")

        async with uow:
            await CurrencyService.delete_currency_by_ticker(uow=uow, ticker="EUR")

        uow.currencies.delete_one.assert_awaited_once_with(ticker="EUR")
        assert uow.committed is True

    async def test_raises_not_found_when_missing(self, uow):
        uow.currencies.delete_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await CurrencyService.delete_currency_by_ticker(uow=uow, ticker="XXX")

        assert exc_info.value.message == Messages.CURRENCY_NOT_FOUND

    async def test_raises_conflict_when_currency_is_linked_to_an_account(self, uow):
        uow.currencies.delete_one.side_effect = fk_violation()

        with pytest.raises(ConflictError) as exc_info:
            async with uow:
                await CurrencyService.delete_currency_by_ticker(uow=uow, ticker="USD")

        assert exc_info.value.message == Messages.CURRENCY_IN_USE
        assert uow.rolled_back is True
        assert uow.committed is False
