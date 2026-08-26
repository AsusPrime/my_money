from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from pydantic import ConfigDict


class BalanceResponseSchema(BaseModel):
    id: int
    name: str
    account_id: int
    group_id: int | None
    is_archived: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BalanceCreateSchema(BaseModel):
    name: str
    account_id: int
    group_id: int | None = None


class BalanceUpdateSchema(BaseModel):
    name: str | None = None
    group_id: int | None = None


class BalanceListResponseSchema(BaseModel):
    items: list[BalanceResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class BalanceAmountsResponseSchema(BaseModel):
    amounts: dict[str, Decimal]


class BalanceTotalResponseSchema(BaseModel):
    total: Decimal
    currency_ticker: str
