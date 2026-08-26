from pydantic import BaseModel
from pydantic import ConfigDict


class BalanceGroupResponseSchema(BaseModel):
    id: int
    name: str
    account_id: int

    model_config = ConfigDict(from_attributes=True)


class BalanceGroupCreateSchema(BaseModel):
    name: str
    account_id: int


class BalanceGroupUpdateSchema(BaseModel):
    name: str | None = None


class BalanceGroupListResponseSchema(BaseModel):
    items: list[BalanceGroupResponseSchema]

    model_config = ConfigDict(from_attributes=True)
