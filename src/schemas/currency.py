from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from src.enums.enums import CurrencyTypeEnum


class CurrencyResponseSchema(BaseModel):
    ticker: str
    name: str | None
    currency_type: CurrencyTypeEnum
    decimal_places: int

    model_config = ConfigDict(from_attributes=True)


class CurrencyCreateSchema(BaseModel):
    ticker: str
    name: str | None = None
    currency_type: CurrencyTypeEnum
    decimal_places: int | None = Field(default=None, ge=0)


class CurrencyUpdateSchema(BaseModel):
    name: str | None = None
    currency_type: CurrencyTypeEnum | None = None
    decimal_places: int | None = Field(default=None, ge=0)


class CurrencyListResponseSchema(BaseModel):
    items: list[CurrencyResponseSchema]

    model_config = ConfigDict(from_attributes=True)
