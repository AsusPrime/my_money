from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from pydantic import ConfigDict


class AccountResponseSchema(BaseModel):
    id: int
    name: str
    is_archived: bool
    base_currency_ticker: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountCreateSchema(BaseModel):
    name: str
    base_currency_ticker: str = "USD"


class AccountUpdateSchema(BaseModel):
    name: str | None = None
    base_currency_ticker: str | None = None


class AccountListResponseSchema(BaseModel):
    items: list[AccountResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class AccountTotalResponseSchema(BaseModel):
    total: Decimal
    currency_ticker: str
