from datetime import datetime
from pydantic import BaseModel
from pydantic import ConfigDict


class BalanceResponseSchema(BaseModel):
    id: int
    name: str
    account_id: int
    is_archived: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BalanceCreateSchema(BaseModel):
    name: str
    account_id: int


class BalanceUpdateSchema(BaseModel):
    name: str | None = None


class BalanceListResponseSchema(BaseModel):
    items: list[BalanceResponseSchema]

    model_config = ConfigDict(from_attributes=True)
