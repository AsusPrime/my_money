from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import model_validator

from src.enums.enums import OperationTypeEnum


class LedgerResponseSchema(BaseModel):
    id: int
    operation_id: UUID | None
    balance_id: int
    currency_ticker: str
    amount: Decimal
    operation_type: OperationTypeEnum
    counterparty: str | None
    note: str | None
    executed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LedgerListResponseSchema(BaseModel):
    items: list[LedgerResponseSchema]

    model_config = ConfigDict(from_attributes=True)


# --- record_operation payloads: one shape per kind of operation, discriminated by `operation_type` ---
# router/API only ever builds one of these and calls LedgerService.record_operation(uow, payload) —
# it never has to know which internal method (single-leg / transfer / trade) handles it.

class _FeeLegMixin(BaseModel):
    """Shared by transfer/trade — an optional 3rd leg sharing the parent operation_id."""

    note: str | None = None
    fee_amount: Decimal | None = None
    fee_currency_ticker: str | None = None


class RecordSingleLegOperationPayload(BaseModel):
    """Covers income / expense / standalone fee — mechanically identical (one balance,
    one leg), they only differ by `type`."""

    operation_type: OperationTypeEnum
    balance_id: int
    amount: Decimal
    currency_ticker: str
    operation_id: UUID | None = None
    counterparty: str | None = None
    note: str | None = None


class RecordTransferPayload(_FeeLegMixin):
    """`amount` — how much leaves from_balance_id. `received_amount` — how much
    actually arrives at to_balance_id; defaults to `amount` (nothing lost in
    transit). Set it lower than `amount` when a fee was taken out of the transfer
    itself rather than charged separately (see `fee_amount`/`fee_currency_ticker`
    on `_FeeLegMixin` for that separate case)."""

    operation_type: OperationTypeEnum
    from_balance_id: int
    to_balance_id: int
    amount: Decimal
    received_amount: Decimal | None = None
    currency_ticker: str

    @model_validator(mode="after")
    def _default_received_amount_to_amount(self) -> "RecordTransferPayload":
        if self.received_amount is None:
            self.received_amount = self.amount
        return self


class RecordTradePayload(_FeeLegMixin):
    operation_type: OperationTypeEnum
    balance_id: int
    spend_amount: Decimal
    spend_currency_ticker: str
    receive_amount: Decimal
    receive_currency_ticker: str
