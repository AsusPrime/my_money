from datetime import datetime
from datetime import timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.enums.enums import AmountModeEnum
from src.enums.enums import OperationTypeEnum
from src.enums.enums import RecurrenceIntervalEnum


@pytest.fixture
def uow():
    return SimpleNamespace(ledgers=AsyncMock())


def make_balance_row(id: int = 1, is_archived: bool = False) -> SimpleNamespace:
    return SimpleNamespace(id=id, is_archived=is_archived)


def make_category_row(id: int = 1, name: str = "Salary") -> SimpleNamespace:
    return SimpleNamespace(id=id, name=name)


def make_recurring_operation_row(
    id: int = 1,
    operation_type: OperationTypeEnum = OperationTypeEnum.INCOME,
    balance_id: int = 1,
    currency_ticker: str = "USD",
    amount_mode: AmountModeEnum = AmountModeEnum.FIXED,
    amount_value: Decimal = Decimal("50"),
    category_id: int | None = None,
    counterparty: str | None = None,
    note: str | None = None,
    interval: RecurrenceIntervalEnum = RecurrenceIntervalEnum.MONTHLY,
    day_of_month: int | None = 1,
    day_of_week: int | None = None,
    month: int | None = None,
    hour: int = 0,
    minute: int = 0,
    last_run_at: datetime | None = None,
    is_active: bool = True,
    created_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        operation_type=operation_type,
        balance_id=balance_id,
        currency_ticker=currency_ticker,
        amount_mode=amount_mode,
        amount_value=amount_value,
        category_id=category_id,
        counterparty=counterparty,
        note=note,
        interval=interval,
        day_of_month=day_of_month,
        day_of_week=day_of_week,
        month=month,
        hour=hour,
        minute=minute,
        last_run_at=last_run_at,
        is_active=is_active,
        created_at=created_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
