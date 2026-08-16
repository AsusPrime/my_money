from decimal import Decimal

from src.enums.enums import OperationTypeEnum
from src.schemas.ledger import RecordTransferPayload


class TestRecordTransferPayloadReceivedAmount:
    def test_defaults_to_amount_when_not_given(self):
        payload = RecordTransferPayload(
            operation_type=OperationTypeEnum.TRANSFER,
            from_balance_id=1,
            to_balance_id=2,
            amount=Decimal("100"),
            currency_ticker="USD",
        )

        assert payload.received_amount == Decimal("100")

    def test_keeps_explicit_value_when_lower_than_amount(self):
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

    def test_keeps_explicit_value_when_equal_to_amount(self):
        payload = RecordTransferPayload(
            operation_type=OperationTypeEnum.TRANSFER,
            from_balance_id=1,
            to_balance_id=2,
            amount=Decimal("100"),
            received_amount=Decimal("100"),
            currency_ticker="USD",
        )

        assert payload.received_amount == Decimal("100")
