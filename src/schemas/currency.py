from pydantic import BaseModel
from pydantic import ConfigDict

from src.enums.enums import CurrencyTypeEnum


class CurrencyResponseSchema(BaseModel):
    ticker: str
    name: str | None
    currency_type: CurrencyTypeEnum

    model_config = ConfigDict(from_attributes=True)


class CurrencyCreateSchema(BaseModel):
    ticker: str
    name: str | None = None
    currency_type: CurrencyTypeEnum


class CurrencyUpdateSchema(BaseModel):
    name: str | None = None
    currency_type: CurrencyTypeEnum | None = None


class CurrencyListResponseSchema(BaseModel):
    items: list[CurrencyResponseSchema]

    model_config = ConfigDict(from_attributes=True)
