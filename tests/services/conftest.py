from datetime import datetime
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.utils.uow.unitofwork import IUnitOfWork


class FakeUnitOfWork(IUnitOfWork):
    def __init__(self):
        self.accounts = AsyncMock()
        self.currencies = AsyncMock()
        self.balances = AsyncMock()
        self.ledgers = AsyncMock()
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
    created_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        name=name,
        base_currency_ticker=base_currency_ticker,
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
