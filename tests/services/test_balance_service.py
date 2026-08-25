from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import ConflictError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.schemas.balance import BalanceCreateSchema
from src.schemas.balance import BalanceUpdateSchema
from src.services.balance_service import BalanceService
from tests.services.conftest import make_account_row
from tests.services.conftest import make_balance_row
from tests.services.conftest import make_currency_row


class TestGetAllBalancesByAccountId:
    async def test_returns_all_balances_for_account(self, uow):
        uow.balances.find_all_by_account_id.return_value = [
            make_balance_row(id=1, name="Cash"),
            make_balance_row(id=2, name="Card"),
        ]

        result = await BalanceService.get_all_balances_by_account_id(uow=uow, account_id=1)

        assert [b.name for b in result.items] == ["Cash", "Card"]

    async def test_returns_empty_list_when_no_balances(self, uow):
        uow.balances.find_all_by_account_id.return_value = []

        result = await BalanceService.get_all_balances_by_account_id(uow=uow, account_id=1)

        assert result.items == []


class TestGetBalanceById:
    async def test_returns_balance_when_found(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, name="Cash")

        result = await BalanceService.get_balance_by_id(uow=uow, balance_id=1)

        assert result.name == "Cash"

    async def test_raises_not_found_when_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await BalanceService.get_balance_by_id(uow=uow, balance_id=999)

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND


class TestCreateBalance:
    async def test_creates_balance(self, uow):
        uow.balances.add_one.return_value = make_balance_row(id=1, name="Cash", account_id=1)

        result = await BalanceService.create_balance(
            uow=uow, balance_data=BalanceCreateSchema(name="Cash", account_id=1)
        )

        assert result.name == "Cash"
        uow.balances.add_one.assert_awaited_once_with(data={"name": "Cash", "account_id": 1})

    async def test_raises_add_record_error_when_insert_fails(self, uow):
        uow.balances.add_one.return_value = None

        with pytest.raises(AddRecordError) as exc_info:
            await BalanceService.create_balance(
                uow=uow, balance_data=BalanceCreateSchema(name="Cash", account_id=1)
            )

        assert exc_info.value.message == Messages.ERROR_FILLED_TO_ADD_NEW_BALANCE


class TestUpdateBalance:
    async def test_updates_balance_when_found(self, uow):
        uow.balances.edit_one.return_value = make_balance_row(id=1, name="Renamed")

        result = await BalanceService.update_balance(
            uow=uow, balance_id=1, balance_data=BalanceUpdateSchema(name="Renamed")
        )

        assert result.name == "Renamed"

    async def test_raises_not_found_when_missing(self, uow):
        uow.balances.edit_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await BalanceService.update_balance(
                uow=uow, balance_id=999, balance_data=BalanceUpdateSchema(name="Renamed")
            )

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND

    async def test_only_sends_fields_that_were_set(self, uow):
        uow.balances.edit_one.return_value = make_balance_row(id=1, name="Cash")

        await BalanceService.update_balance(uow=uow, balance_id=1, balance_data=BalanceUpdateSchema())

        uow.balances.edit_one.assert_awaited_once_with(id=1, data={})


class TestArchiveBalance:
    async def test_raises_not_found_when_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await BalanceService.archive_balance(uow=uow, balance_id=999)

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND

    async def test_archives_balance(self, uow):
        row = make_balance_row(id=1, is_archived=False)
        uow.balances.find_one_or_none.return_value = row

        async with uow:
            await BalanceService.archive_balance(uow=uow, balance_id=1)

        assert row.is_archived is True
        assert uow.committed is True

    async def test_archives_balance_even_with_nonzero_amount(self, uow):
        row = make_balance_row(id=1, is_archived=False)
        uow.balances.find_one_or_none.return_value = row
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("150.50")}

        await BalanceService.archive_balance(uow=uow, balance_id=1)

        assert row.is_archived is True


class TestGetActiveBalanceById:
    async def test_returns_balance_when_found_and_not_archived(self, uow):
        row = make_balance_row(id=1, is_archived=False)
        uow.balances.find_one_or_none.return_value = row

        result = await BalanceService.get_active_balance_by_id(uow=uow, balance_id=1)

        assert result is row

    async def test_raises_not_found_when_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await BalanceService.get_active_balance_by_id(uow=uow, balance_id=999)

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND

    async def test_raises_conflict_when_archived(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=True)

        with pytest.raises(ConflictError) as exc_info:
            await BalanceService.get_active_balance_by_id(uow=uow, balance_id=1)

        assert exc_info.value.message == Messages.BALANCE_IS_ARCHIVED


class TestGetBalanceAmounts:
    async def test_returns_amounts_grouped_by_currency(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1)
        uow.ledgers.get_amounts_by_balance_id.return_value = {
            "USD": Decimal("150.50"),
            "EUR": Decimal("10"),
        }

        result = await BalanceService.get_balance_amounts(uow=uow, balance_id=1)

        assert result.amounts == {"USD": Decimal("150.50"), "EUR": Decimal("10")}

    async def test_returns_empty_dict_when_no_ledger_rows(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1)
        uow.ledgers.get_amounts_by_balance_id.return_value = {}

        result = await BalanceService.get_balance_amounts(uow=uow, balance_id=1)

        assert result.amounts == {}

    async def test_raises_not_found_when_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await BalanceService.get_balance_amounts(uow=uow, balance_id=999)

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND


class TestGetBalanceTotal:
    async def test_returns_the_amount_directly_when_only_base_currency_is_held(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, account_id=1)
        uow.accounts.find_one_or_none.return_value = make_account_row(
            id=1, base_currency_ticker="UAH"
        )
        uow.ledgers.get_amounts_by_balance_id.return_value = {"UAH": Decimal("500")}

        result = await BalanceService.get_balance_total(uow=uow, balance_id=1)

        assert result.total == Decimal("500")
        assert result.currency_ticker == "UAH"

    async def test_converts_a_foreign_currency_using_the_current_rate(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, account_id=1)
        uow.accounts.find_one_or_none.return_value = make_account_row(
            id=1, base_currency_ticker="UAH"
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="EUR")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"EUR": Decimal("100")}
        exchange_rate_service = AsyncMock()
        exchange_rate_service.get_current_rate.return_value = Decimal("45")

        result = await BalanceService.get_balance_total(
            uow=uow, balance_id=1, exchange_rate_service=exchange_rate_service
        )

        assert result.total == Decimal("4500")
        exchange_rate_service.get_current_rate.assert_awaited_once_with(
            currency_ticker="EUR", base_currency_ticker="UAH", currency_type="fiat"
        )

    async def test_sums_base_and_foreign_currencies_together(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, account_id=1)
        uow.accounts.find_one_or_none.return_value = make_account_row(
            id=1, base_currency_ticker="UAH"
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {
            "UAH": Decimal("100"),
            "USD": Decimal("10"),
        }
        exchange_rate_service = AsyncMock()
        exchange_rate_service.get_current_rate.return_value = Decimal("41")

        result = await BalanceService.get_balance_total(
            uow=uow, balance_id=1, exchange_rate_service=exchange_rate_service
        )

        assert result.total == Decimal("510")

    async def test_raises_not_found_when_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await BalanceService.get_balance_total(uow=uow, balance_id=999)

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND
