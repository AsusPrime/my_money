from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def uow():
    return SimpleNamespace(ledgers=AsyncMock())


def make_balance_row(id: int = 1, is_archived: bool = False) -> SimpleNamespace:
    return SimpleNamespace(id=id, is_archived=is_archived)


def make_category_row(id: int = 1, name: str = "Salary") -> SimpleNamespace:
    return SimpleNamespace(id=id, name=name)
