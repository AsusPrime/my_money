from decimal import Decimal

from src.enums.enums import OperationTypeEnum
from src.schemas.ledger import RecordSingleLegOperationPayload
from src.schemas.ledger import RecordTransferPayload


class TestRecordTransferPayloadReceivedFields:
    """received_amount/received_currency_ticker are plain optional fields here —
    defaulting and cross-currency validation live in LedgerService._transfer,
    not in the schema (see tests/services/test_ledger_service.py)."""

    def test_stays_none_when_not_given(self):
        payload = RecordTransferPayload(
            operation_type=OperationTypeEnum.TRANSFER,
            from_balance_id=1,
            to_balance_id=2,
            amount=Decimal("100"),
            currency_ticker="USD",
        )

        assert payload.received_amount is None
        assert payload.received_currency_ticker is None

    def test_keeps_explicit_received_amount(self):
        payload = RecordTransferPayload(
            operation_type=OperationTypeEnum.TRANSFER,
            from_balance_id=1,
            to_balance_id=2,
            amount=Decimal("100"),
            received_amount=Decimal("99"),
            currency_ticker="USD",
        )

        assert payload.received_amount == Decimal("99")
        assert payload.amount == Decimal("100")

    def test_keeps_explicit_received_currency_ticker(self):
        payload = RecordTransferPayload(
            operation_type=OperationTypeEnum.TRANSFER,
            from_balance_id=1,
            to_balance_id=2,
            amount=Decimal("1000"),
            currency_ticker="UAH",
            received_amount=Decimal("25"),
            received_currency_ticker="USDT",
        )

        assert payload.received_currency_ticker == "USDT"
        assert payload.received_amount == Decimal("25")


class TestRecordSingleLegOperationPayloadCategory:
    def test_category_id_defaults_to_none(self):
        payload = RecordSingleLegOperationPayload(
            operation_type=OperationTypeEnum.EXPENSE,
            balance_id=1,
            amount=Decimal("50"),
            currency_ticker="USD",
        )

        assert payload.category_id is None

    def test_accepts_explicit_category_id(self):
        payload = RecordSingleLegOperationPayload(
            operation_type=OperationTypeEnum.EXPENSE,
            balance_id=1,
            amount=Decimal("50"),
            currency_ticker="USD",
            category_id=3,
        )

        assert payload.category_id == 3
