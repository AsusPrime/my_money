import pytest

from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.schemas.account import AccountCreateSchema
from src.schemas.account import AccountUpdateSchema
from src.services.account_service import AccountService
from tests.services.conftest import make_account_row
from tests.services.conftest import make_currency_row


class TestGetAllAccounts:
    async def test_returns_all_accounts(self, uow):
        uow.accounts.find_all.return_value = [
            make_account_row(id=1, name="Monobank"),
            make_account_row(id=2, name="Binance"),
        ]

        async with uow:
            result = await AccountService.get_all_accounts(uow=uow)

        assert [a.name for a in result.items] == ["Monobank", "Binance"]
        assert uow.committed is True

    async def test_returns_empty_list_when_no_accounts(self, uow):
        uow.accounts.find_all.return_value = []

        result = await AccountService.get_all_accounts(uow=uow)

        assert result.items == []


class TestGetAccountById:
    async def test_returns_account_when_found(self, uow):
        uow.accounts.find_one_or_none.return_value = make_account_row(id=1, name="Monobank")

        result = await AccountService.get_account_by_id(uow=uow, account_id=1)

        assert result.id == 1
        assert result.name == "Monobank"
        uow.accounts.find_one_or_none.assert_awaited_once_with(id=1)

    async def test_raises_not_found_when_missing(self, uow):
        uow.accounts.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await AccountService.get_account_by_id(uow=uow, account_id=999)

        assert exc_info.value.message == Messages.ACCOUNT_NOT_FOUND


class TestCreateAccount:
    async def test_creates_account_when_currency_exists(self, uow):
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.accounts.add_one.return_value = make_account_row(name="Monobank", base_currency_ticker="USD")

        result = await AccountService.create_account(
            uow=uow,
            account_data=AccountCreateSchema(name="Monobank", base_currency_ticker="USD"),
        )

        assert result.name == "Monobank"
        assert result.base_currency_ticker == "USD"
        uow.accounts.add_one.assert_awaited_once()

    async def test_raises_not_found_when_base_currency_does_not_exist(self, uow):
        uow.currencies.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            async with uow:
                await AccountService.create_account(
                    uow=uow,
                    account_data=AccountCreateSchema(name="Monobank", base_currency_ticker="XXX"),
                )

        assert exc_info.value.message == Messages.CURRENCY_NOT_FOUND
        uow.accounts.add_one.assert_not_called()
        assert uow.rolled_back is True

    async def test_raises_add_record_error_when_insert_fails(self, uow):
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.accounts.add_one.return_value = None

        with pytest.raises(AddRecordError) as exc_info:
            await AccountService.create_account(
                uow=uow,
                account_data=AccountCreateSchema(name="Monobank", base_currency_ticker="USD"),
            )

        assert exc_info.value.message == Messages.ERROR_FILLED_TO_ADD_NEW_ACCOUNT


class TestUpdateAccountById:
    async def test_updates_account_without_touching_currency_check(self, uow):
        uow.accounts.edit_one.return_value = make_account_row(id=1, name="New name")

        result = await AccountService.update_account_by_id(
            uow=uow, account_id=1, account_data=AccountUpdateSchema(name="New name")
        )

        assert result.name == "New name"
        uow.currencies.find_one_or_none.assert_not_called()

    async def test_updates_base_currency_when_it_exists(self, uow):
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="EUR")
        uow.accounts.edit_one.return_value = make_account_row(id=1, base_currency_ticker="EUR")

        result = await AccountService.update_account_by_id(
            uow=uow,
            account_id=1,
            account_data=AccountUpdateSchema(base_currency_ticker="EUR"),
        )

        assert result.base_currency_ticker == "EUR"

    async def test_raises_not_found_when_new_base_currency_does_not_exist(self, uow):
        uow.currencies.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await AccountService.update_account_by_id(
                uow=uow,
                account_id=1,
                account_data=AccountUpdateSchema(base_currency_ticker="XXX"),
            )

        assert exc_info.value.message == Messages.CURRENCY_NOT_FOUND
        uow.accounts.edit_one.assert_not_called()

    async def test_raises_not_found_when_account_missing(self, uow):
        uow.accounts.edit_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await AccountService.update_account_by_id(
                uow=uow, account_id=999, account_data=AccountUpdateSchema(name="X")
            )

        assert exc_info.value.message == Messages.ACCOUNT_NOT_FOUND


class TestDeleteAccountById:
    async def test_deletes_account_when_found(self, uow):
        uow.accounts.delete_one.return_value = make_account_row(id=1)

        async with uow:
            await AccountService.delete_account_by_id(uow=uow, account_id=1)

        uow.accounts.delete_one.assert_awaited_once_with(_id=1)
        assert uow.committed is True

    async def test_raises_not_found_when_missing(self, uow):
        uow.accounts.delete_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await AccountService.delete_account_by_id(uow=uow, account_id=999)

        assert exc_info.value.message == Messages.ACCOUNT_NOT_FOUND
