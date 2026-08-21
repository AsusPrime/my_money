from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from src.enums.enums import OperationTypeEnum


class LedgerResponseSchema(BaseModel):
    id: int
    operation_id: UUID | None
    balance_id: int
    currency_ticker: str
    amount: Decimal
    operation_type: OperationTypeEnum
    category_id: int | None
    counterparty: str | None
    note: str | None
    executed_at: datetime
    base_currency_rate: Decimal | None

    model_config = ConfigDict(from_attributes=True)


class LedgerListResponseSchema(BaseModel):
    items: list[LedgerResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class LedgerUpdateSchema(BaseModel):
    amount: Decimal | None = None
    category_id: int | None = None
    counterparty: str | None = None
    note: str | None = None
    base_currency_rate: Decimal | None = None


class _FeeLegMixin(BaseModel):
    note: str | None = None
    fee_amount: Decimal | None = None
    fee_currency_ticker: str | None = None


class RecordSingleLegOperationPayload(BaseModel):
    operation_type: OperationTypeEnum
    balance_id: int
    amount: Decimal
    currency_ticker: str
    operation_id: UUID | None = None
    category_id: int | None = None
    counterparty: str | None = None
    note: str | None = None
    executed_at: datetime | None = None
    base_currency_rate: Decimal | None = None


class RecordTransferPayload(_FeeLegMixin):
    """`amount`/`currency_ticker` — how much leaves from_balance_id, and in what
    currency. `received_amount`/`received_currency_ticker` — how much actually
    arrives at to_balance_id, and in what currency; optional, resolved by
    LedgerService._transfer (not here) — same-currency transfers default
    received_amount to amount and received_currency_ticker to currency_ticker,
    while a currency-converting transfer (e.g. bank UAH -> exchange USDT via a
    P2P sale) requires received_amount to be given explicitly."""

    operation_type: OperationTypeEnum
    from_balance_id: int
    to_balance_id: int
    amount: Decimal
    received_amount: Decimal | None = None
    currency_ticker: str
    received_currency_ticker: str | None = None
    executed_at: datetime | None = None
    base_currency_rate: Decimal | None = None


class RecordTradePayload(_FeeLegMixin):
    operation_type: OperationTypeEnum
    balance_id: int
    spend_amount: Decimal
    spend_currency_ticker: str
    receive_amount: Decimal
    receive_currency_ticker: str
    executed_at: datetime | None = None
    base_currency_rate: Decimal | None = None
