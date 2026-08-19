from datetime import datetime
from datetime import timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID
from uuid import uuid4

import pytest

from src.enums.enums import OperationTypeEnum
from src.utils.uow.unitofwork import IUnitOfWork


class FakeUnitOfWork(IUnitOfWork):
    def __init__(self):
        self.accounts = AsyncMock()
        self.currencies = AsyncMock()
        self.balances = AsyncMock()
        self.ledgers = AsyncMock()
        self.categories = AsyncMock()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        return False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.fixture
def uow():
    return FakeUnitOfWork()


def make_account_row(
    id: int = 1,
    name: str = "Main",
    base_currency_ticker: str = "USD",
    is_archived: bool = False,
    created_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        name=name,
        base_currency_ticker=base_currency_ticker,
        is_archived=is_archived,
        created_at=created_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_currency_row(
    ticker: str = "USD",
    name: str | None = "US Dollar",
    currency_type: str = "fiat",
) -> SimpleNamespace:
    return SimpleNamespace(
        ticker=ticker,
        name=name,
        currency_type=currency_type,
    )


def make_category_row(
    id: int = 1,
    name: str = "Salary",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        name=name,
    )


def make_balance_row(
    id: int = 1,
    name: str = "Cash",
    account_id: int = 1,
    is_archived: bool = False,
    created_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        name=name,
        account_id=account_id,
        is_archived=is_archived,
        created_at=created_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


_UNSET = object()


def make_ledger_row(
    id: int = 1,
    operation_id: UUID | None = _UNSET,
    balance_id: int = 1,
    currency_ticker: str = "USD",
    amount: Decimal = Decimal("100"),
    operation_type: OperationTypeEnum = OperationTypeEnum.INCOME,
    category_id: int | None = None,
    counterparty: str | None = None,
    note: str | None = None,
    executed_at: datetime | None = None,
) -> SimpleNamespace:
    if operation_id is _UNSET:
        operation_id = uuid4()
    return SimpleNamespace(
        id=id,
        operation_id=operation_id,
        balance_id=balance_id,
        currency_ticker=currency_ticker,
        amount=amount,
        operation_type=operation_type,
        category_id=category_id,
        counterparty=counterparty,
        note=note,
        executed_at=executed_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
