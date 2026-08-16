from decimal import Decimal

import pytest

from src.core.exceptions.exceptions import ConflictError
from src.core.messages.messages import Messages
from src.entities.balance import BalanceEntity
from tests.entities.conftest import make_balance_row


class TestGetAmount:
    async def test_returns_amounts_grouped_by_currency(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {
            "USD": Decimal("100"),
            "EUR": Decimal("15"),
        }
        entity = BalanceEntity(balance=make_balance_row(id=1), uow=uow)

        result = await entity.get_amounts()

        assert result == {"USD": Decimal("100"), "EUR": Decimal("15")}
        uow.ledgers.get_amounts_by_balance_id.assert_awaited_once_with(balance_id=1)


class TestIsEmpty:
    async def test_true_when_balance_has_no_ledger_rows(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {}

        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        assert await entity._is_empty() is True

    async def test_true_when_all_currency_sums_are_zero(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {
            "USD": Decimal("0"),
            "EUR": Decimal("0"),
        }

        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        assert await entity._is_empty() is True

    async def test_false_when_any_currency_is_positive(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {
            "USD": Decimal("0"),
            "EUR": Decimal("15"),
        }

        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        assert await entity._is_empty() is False

    async def test_false_when_currency_is_negative(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("-5")}

        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        assert await entity._is_empty() is False


class TestArchive:
    async def test_archives_balance_when_empty(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {}
        row = make_balance_row(is_archived=False)
        entity = BalanceEntity(balance=row, uow=uow)

        await entity.archive()

        assert row.is_archived is True

    async def test_raises_conflict_when_balance_has_nonzero_amount(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("50")}
        row = make_balance_row(is_archived=False)
        entity = BalanceEntity(balance=row, uow=uow)

        with pytest.raises(ConflictError) as exc_info:
            await entity.archive()

        assert exc_info.value.message == Messages.BALANCE_HAS_NONZERO_AMOUNT
        assert row.is_archived is False


class TestEnsureSufficientFunds:
    async def test_passes_when_currency_has_enough_funds(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("100")}
        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        await entity.ensure_sufficient_funds(currency_ticker="USD", amount=Decimal("-40"))

    async def test_passes_when_result_is_exactly_zero(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("100")}
        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        await entity.ensure_sufficient_funds(currency_ticker="USD", amount=Decimal("-100"))

    async def test_raises_conflict_when_amount_exceeds_current_funds(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("100")}
        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        with pytest.raises(ConflictError) as exc_info:
            await entity.ensure_sufficient_funds(currency_ticker="USD", amount=Decimal("-150"))

        assert exc_info.value.message == Messages.BALANCE_INSUFFICIENT_FUNDS

    async def test_raises_conflict_when_currency_is_not_on_the_balance_at_all(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("100")}
        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        with pytest.raises(ConflictError) as exc_info:
            await entity.ensure_sufficient_funds(currency_ticker="EUR", amount=Decimal("-1"))

        assert exc_info.value.message == Messages.BALANCE_INSUFFICIENT_FUNDS

    async def test_passes_for_a_positive_amount_regardless_of_current_funds(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("0")}
        entity = BalanceEntity(balance=make_balance_row(), uow=uow)

        await entity.ensure_sufficient_funds(currency_ticker="USD", amount=Decimal("500"))
