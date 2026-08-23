from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from pydantic import ConfigDict

from src.enums.enums import AmountModeEnum
from src.enums.enums import OperationTypeEnum
from src.enums.enums import RecurrenceIntervalEnum


class RecurringOperationResponseSchema(BaseModel):
    id: int
    operation_type: OperationTypeEnum
    balance_id: int
    currency_ticker: str
    amount_mode: AmountModeEnum
    amount_value: Decimal
    category_id: int | None
    counterparty: str | None
    note: str | None
    interval: RecurrenceIntervalEnum
    day_of_month: int | None
    day_of_week: int | None
    month: int | None
    hour: int
    minute: int
    last_run_at: datetime | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RecurringOperationListResponseSchema(BaseModel):
    items: list[RecurringOperationResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class RecurringOperationCreateSchema(BaseModel):
    operation_type: OperationTypeEnum
    balance_id: int
    currency_ticker: str
    amount_mode: AmountModeEnum
    amount_value: Decimal
    category_id: int | None = None
    counterparty: str | None = None
    note: str | None = None
    interval: RecurrenceIntervalEnum
    day_of_month: int | None = None
    day_of_week: int | None = None
    month: int | None = None
    hour: int = 0
    minute: int = 0


class RecurringOperationUpdateSchema(BaseModel):
    amount_mode: AmountModeEnum | None = None
    amount_value: Decimal | None = None
    category_id: int | None = None
    counterparty: str | None = None
    note: str | None = None
    is_active: bool | None = None
