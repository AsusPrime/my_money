from decimal import Decimal
from uuid import uuid4

import pytest

from src.enums.enums import CurrencyTypeEnum
from src.enums.enums import OperationTypeEnum
from src.repositories.account import AccountRepository
from src.repositories.balance import BalanceRepository
from src.repositories.currency import CurrencyRepository
from src.repositories.ledger import LedgerRepository

pytestmark = pytest.mark.integration


async def _make_account(session, base_currency_ticker: str = "USD") -> int:
    await CurrencyRepository(session).add_one(
        data={"ticker": base_currency_ticker, "currency_type": CurrencyTypeEnum.FIAT}
    )
    account = await AccountRepository(session).add_one(
        data={"name": "Main", "base_currency_ticker": base_currency_ticker}
    )
    return account["id"]


async def _make_balance(session, account_id: int, name: str = "Cash") -> int:
    balance = await BalanceRepository(session).add_one(data={"name": name, "account_id": account_id})
    return balance["id"]


class TestGetAmountsByBalanceId:
    async def test_groups_and_sums_by_currency(self, session):
        account_id = await _make_account(session)
        await CurrencyRepository(session).add_one(
            data={"ticker": "EUR", "currency_type": CurrencyTypeEnum.FIAT}
        )
        balance_id = await _make_balance(session, account_id)
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("100"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-30"), "operation_type": OperationTypeEnum.EXPENSE,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "EUR",
                "amount": Decimal("15"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        result = await ledger_repo.get_amounts_by_balance_id(balance_id=balance_id)

        assert result == {"USD": Decimal("70"), "EUR": Decimal("15")}

    async def test_returns_empty_dict_when_no_ledger_rows(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id, name="Empty")
        await session.commit()

        result = await LedgerRepository(session).get_amounts_by_balance_id(balance_id=balance_id)

        assert result == {}

    async def test_only_sums_rows_for_the_given_balance(self, session):
        account_id = await _make_account(session)
        balance_a = await _make_balance(session, account_id, name="A")
        balance_b = await _make_balance(session, account_id, name="B")
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_a, "currency_ticker": "USD",
                "amount": Decimal("50"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_b, "currency_ticker": "USD",
                "amount": Decimal("999"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        result = await ledger_repo.get_amounts_by_balance_id(balance_id=balance_a)

        assert result == {"USD": Decimal("50")}
