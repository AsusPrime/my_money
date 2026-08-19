from datetime import datetime
from datetime import timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.core.exceptions.exceptions import BadRequestError
from src.core.exceptions.exceptions import ConflictError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.enums.enums import OperationTypeEnum
from src.schemas.ledger import LedgerUpdateSchema
from src.schemas.ledger import RecordSingleLegOperationPayload
from src.schemas.ledger import RecordTradePayload
from src.schemas.ledger import RecordTransferPayload
from src.services.ledger_service import LedgerService
from tests.services.conftest import make_balance_row
from tests.services.conftest import make_currency_row
from tests.services.conftest import make_ledger_row


class TestRecordSingleLegOperation:
    @pytest.mark.parametrize(
        "operation_type,input_amount,expected_amount",
        [
            (OperationTypeEnum.INCOME, Decimal("500"), Decimal("500")),
            (OperationTypeEnum.EXPENSE, Decimal("40"), Decimal("-40")),
            (OperationTypeEnum.FEE, Decimal("2.5"), Decimal("-2.5")),
        ],
    )
    async def test_creates_a_single_leg_with_given_operation_type(
        self, uow, operation_type, input_amount, expected_amount
    ):
        # callers always pass a positive magnitude — the service decides the sign
        # based on operation_type (income/receive -> +, expense/fee -> -)
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1,
            currency_ticker="USD",
            amount=expected_amount,
            operation_type=operation_type,
        )

        result = await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=operation_type,
                balance_id=1,
                amount=input_amount,
                currency_ticker="USD",
            ),
        )

        _, kwargs = uow.ledgers.add_one.await_args
        data = kwargs["data"]
        assert data["balance_id"] == 1
        assert data["currency_ticker"] == "USD"
        assert data["amount"] == expected_amount
        assert data["operation_type"] == operation_type
        assert result.amount == expected_amount

    async def test_raises_not_found_when_balance_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService._record_single_leg_operation(
                uow=uow,
                payload=RecordSingleLegOperationPayload(
                    operation_type=OperationTypeEnum.INCOME,
                    balance_id=999,
                    amount=Decimal("500"),
                    currency_ticker="USD",
                ),
            )

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND

    async def test_raises_not_found_when_currency_missing(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1)
        uow.currencies.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService._record_single_leg_operation(
                uow=uow,
                payload=RecordSingleLegOperationPayload(
                    operation_type=OperationTypeEnum.INCOME,
                    balance_id=1,
                    amount=Decimal("500"),
                    currency_ticker="XXX",
                ),
            )

        assert exc_info.value.message == Messages.CURRENCY_NOT_FOUND

    async def test_raises_conflict_when_balance_is_archived(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=True
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")

        with pytest.raises(ConflictError) as exc_info:
            await LedgerService._record_single_leg_operation(
                uow=uow,
                payload=RecordSingleLegOperationPayload(
                    operation_type=OperationTypeEnum.INCOME,
                    balance_id=1,
                    amount=Decimal("500"),
                    currency_ticker="USD",
                ),
            )

        assert exc_info.value.message == Messages.BALANCE_IS_ARCHIVED
        uow.ledgers.add_one.assert_not_called()


class TestRecordSingleLegOperationSignNormalization:
    """The service must enforce the sign itself regardless of what the caller sends —
    callers are expected to always send a positive magnitude, but if a wrongly-signed
    amount slips through anyway, the stored amount must still come out correct."""

    async def test_income_with_negative_input_is_stored_as_positive(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1,
            currency_ticker="USD",
            amount=Decimal("500"),
            operation_type=OperationTypeEnum.INCOME,
        )

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("-500"),
                currency_ticker="USD",
            ),
        )

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["amount"] == Decimal("500")

    async def test_income_with_positive_input_stays_positive(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1,
            currency_ticker="USD",
            amount=Decimal("500"),
            operation_type=OperationTypeEnum.INCOME,
        )

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("500"),
                currency_ticker="USD",
            ),
        )

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["amount"] == Decimal("500")

    async def test_expense_with_positive_input_is_stored_as_negative(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1,
            currency_ticker="USD",
            amount=Decimal("-40"),
            operation_type=OperationTypeEnum.EXPENSE,
        )

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.EXPENSE,
                balance_id=1,
                amount=Decimal("40"),
                currency_ticker="USD",
            ),
        )

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["amount"] == Decimal("-40")

    async def test_expense_with_negative_input_stays_negative(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1,
            currency_ticker="USD",
            amount=Decimal("-40"),
            operation_type=OperationTypeEnum.EXPENSE,
        )

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.EXPENSE,
                balance_id=1,
                amount=Decimal("-40"),
                currency_ticker="USD",
            ),
        )

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["amount"] == Decimal("-40")

    async def test_fee_with_positive_input_is_stored_as_negative(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1,
            currency_ticker="USD",
            amount=Decimal("-2.5"),
            operation_type=OperationTypeEnum.FEE,
        )

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.FEE,
                balance_id=1,
                amount=Decimal("2.5"),
                currency_ticker="USD",
            ),
        )

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["amount"] == Decimal("-2.5")


class TestRecordSingleLegOperationSufficientFunds:
    async def test_raises_conflict_when_expense_exceeds_current_funds(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("50")}

        with pytest.raises(ConflictError) as exc_info:
            await LedgerService._record_single_leg_operation(
                uow=uow,
                payload=RecordSingleLegOperationPayload(
                    operation_type=OperationTypeEnum.EXPENSE,
                    balance_id=1,
                    amount=Decimal("100"),
                    currency_ticker="USD",
                ),
            )

        assert exc_info.value.message == Messages.BALANCE_INSUFFICIENT_FUNDS
        uow.ledgers.add_one.assert_not_called()

    async def test_raises_conflict_when_currency_not_on_balance_at_all(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="EUR")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("1000")}

        with pytest.raises(ConflictError) as exc_info:
            await LedgerService._record_single_leg_operation(
                uow=uow,
                payload=RecordSingleLegOperationPayload(
                    operation_type=OperationTypeEnum.FEE,
                    balance_id=1,
                    amount=Decimal("1"),
                    currency_ticker="EUR",
                ),
            )

        assert exc_info.value.message == Messages.BALANCE_INSUFFICIENT_FUNDS
        uow.ledgers.add_one.assert_not_called()

    async def test_allows_expense_that_exactly_zeroes_the_balance(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("100")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1, amount=Decimal("-100"))

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.EXPENSE,
                balance_id=1,
                amount=Decimal("100"),
                currency_ticker="USD",
            ),
        )

        uow.ledgers.add_one.assert_awaited_once()

    async def test_income_from_a_zero_balance_is_allowed(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("0")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1, amount=Decimal("500"))

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("500"),
                currency_ticker="USD",
            ),
        )

        uow.ledgers.add_one.assert_awaited_once()


class TestRecordSingleLegOperationExecutedAt:
    async def test_passes_explicit_executed_at_through_to_insert(self, uow):
        custom_date = datetime(2026, 1, 15, tzinfo=timezone.utc)
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1, amount=Decimal("500"), executed_at=custom_date
        )

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("500"),
                currency_ticker="USD",
                executed_at=custom_date,
            ),
        )

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["executed_at"] == custom_date

    async def test_defaults_executed_at_to_now_when_not_given(self, uow):
        # must never send executed_at=None explicitly — the column is NOT NULL,
        # so the service must resolve a concrete value itself
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1, amount=Decimal("500"))

        before = datetime.now(timezone.utc)
        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("500"),
                currency_ticker="USD",
            ),
        )
        after = datetime.now(timezone.utc)

        _, kwargs = uow.ledgers.add_one.await_args
        assert before <= kwargs["data"]["executed_at"] <= after


class TestTransfer:
    async def test_creates_two_legs_sharing_one_operation_id(self, uow):
        uow.balances.find_one_or_none.side_effect = [
            make_balance_row(id=1, is_archived=False),
            make_balance_row(id=2, is_archived=False),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(balance_id=1, amount=Decimal("-100")),
            make_ledger_row(balance_id=2, amount=Decimal("100")),
        ]

        result = await LedgerService._transfer(
            uow=uow,
            payload=RecordTransferPayload(
                operation_type=OperationTypeEnum.TRANSFER,
                from_balance_id=1,
                to_balance_id=2,
                amount=Decimal("100"),
                currency_ticker="USD",
            ),
        )

        assert uow.ledgers.add_one.await_count == 2
        first_call = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        second_call = uow.ledgers.add_one.await_args_list[1].kwargs["data"]

        assert first_call["balance_id"] == 1
        assert first_call["amount"] == Decimal("-100")
        assert second_call["balance_id"] == 2
        assert second_call["amount"] == Decimal("100")
        assert first_call["operation_id"] == second_call["operation_id"]
        assert first_call["operation_type"] == OperationTypeEnum.TRANSFER
        assert len(result.items) == 2

    async def test_inflow_leg_uses_received_amount_not_amount(self, uow):
        # a fee was taken out of the transfer itself: 100 left from_balance_id,
        # but only 95 actually arrived at to_balance_id
        uow.balances.find_one_or_none.side_effect = [
            make_balance_row(id=1, is_archived=False),
            make_balance_row(id=2, is_archived=False),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(balance_id=1, amount=Decimal("-100")),
            make_ledger_row(balance_id=2, amount=Decimal("95")),
        ]

        await LedgerService._transfer(
            uow=uow,
            payload=RecordTransferPayload(
                operation_type=OperationTypeEnum.TRANSFER,
                from_balance_id=1,
                to_balance_id=2,
                amount=Decimal("100"),
                received_amount=Decimal("95"),
                currency_ticker="USD",
            ),
        )

        first_call = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        second_call = uow.ledgers.add_one.await_args_list[1].kwargs["data"]

        assert first_call["amount"] == Decimal("-100")
        assert second_call["amount"] == Decimal("95")

    async def test_inflow_leg_uses_received_currency_when_different_from_sent(self, uow):
        # moving value from a bank UAH balance to an exchange USDT balance via a
        # P2P sale — both ends are your own balances, currency changes along the way
        uow.balances.find_one_or_none.side_effect = [
            make_balance_row(id=1, is_archived=False),
            make_balance_row(id=2, is_archived=False),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="UAH")
        uow.balances.get_name_by_id.return_value = "Binance"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"UAH": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(balance_id=1, currency_ticker="UAH", amount=Decimal("-1000")),
            make_ledger_row(balance_id=2, currency_ticker="USDT", amount=Decimal("25")),
        ]

        await LedgerService._transfer(
            uow=uow,
            payload=RecordTransferPayload(
                operation_type=OperationTypeEnum.TRANSFER,
                from_balance_id=1,
                to_balance_id=2,
                amount=Decimal("1000"),
                currency_ticker="UAH",
                received_amount=Decimal("25"),
                received_currency_ticker="USDT",
            ),
        )

        first_call = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        second_call = uow.ledgers.add_one.await_args_list[1].kwargs["data"]

        assert first_call["currency_ticker"] == "UAH"
        assert first_call["amount"] == Decimal("-1000")
        assert second_call["currency_ticker"] == "USDT"
        assert second_call["amount"] == Decimal("25")

    async def test_raises_bad_request_when_received_currency_differs_and_amount_not_given(
        self, uow
    ):
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="UAH")

        with pytest.raises(BadRequestError) as exc_info:
            await LedgerService._transfer(
                uow=uow,
                payload=RecordTransferPayload(
                    operation_type=OperationTypeEnum.TRANSFER,
                    from_balance_id=1,
                    to_balance_id=2,
                    amount=Decimal("1000"),
                    currency_ticker="UAH",
                    received_currency_ticker="USDT",
                ),
            )

        assert exc_info.value.message == Messages.TRANSFER_RECEIVED_AMOUNT_REQUIRED
        uow.ledgers.add_one.assert_not_called()

    async def test_raises_not_found_when_from_balance_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService._transfer(
                uow=uow,
                payload=RecordTransferPayload(
                    operation_type=OperationTypeEnum.TRANSFER,
                    from_balance_id=999,
                    to_balance_id=2,
                    amount=Decimal("100"),
                    currency_ticker="USD",
                ),
            )

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND

    async def test_raises_not_found_when_to_balance_missing(self, uow):
        uow.balances.find_one_or_none.side_effect = [
            make_balance_row(id=1, is_archived=False),
            None,
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1, amount=Decimal("-100"))

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService._transfer(
                uow=uow,
                payload=RecordTransferPayload(
                    operation_type=OperationTypeEnum.TRANSFER,
                    from_balance_id=1,
                    to_balance_id=999,
                    amount=Decimal("100"),
                    currency_ticker="USD",
                ),
            )

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND

    async def test_raises_conflict_when_from_balance_is_archived(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=True
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"

        with pytest.raises(ConflictError) as exc_info:
            await LedgerService._transfer(
                uow=uow,
                payload=RecordTransferPayload(
                    operation_type=OperationTypeEnum.TRANSFER,
                    from_balance_id=1,
                    to_balance_id=2,
                    amount=Decimal("100"),
                    currency_ticker="USD",
                ),
            )

        assert exc_info.value.message == Messages.BALANCE_IS_ARCHIVED
        uow.ledgers.add_one.assert_not_called()

    async def test_fee_leg_shares_the_transfer_operation_id(self, uow):
        uow.balances.find_one_or_none.side_effect = [
            make_balance_row(id=1, is_archived=False),
            make_balance_row(id=2, is_archived=False),
            make_balance_row(id=2, is_archived=False),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(balance_id=1, amount=Decimal("-100")),
            make_ledger_row(balance_id=2, amount=Decimal("100")),
            make_ledger_row(
                balance_id=1, amount=Decimal("-1"), operation_type=OperationTypeEnum.FEE
            ),
        ]

        await LedgerService._transfer(
            uow=uow,
            payload=RecordTransferPayload(
                operation_type=OperationTypeEnum.TRANSFER,
                from_balance_id=1,
                to_balance_id=2,
                amount=Decimal("100"),
                currency_ticker="USD",
                fee_amount=Decimal("-1"),
                fee_currency_ticker="USD",
            ),
        )

        assert uow.ledgers.add_one.await_count == 3
        transfer_leg = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        fee_leg = uow.ledgers.add_one.await_args_list[2].kwargs["data"]

        assert fee_leg["balance_id"] == 1
        assert fee_leg["amount"] == Decimal("-1")
        assert fee_leg["operation_type"] == OperationTypeEnum.FEE
        assert fee_leg["operation_id"] == transfer_leg["operation_id"]

    async def test_propagates_executed_at_to_both_legs(self, uow):
        custom_date = datetime(2026, 1, 15, tzinfo=timezone.utc)
        uow.balances.find_one_or_none.side_effect = [
            make_balance_row(id=1, is_archived=False),
            make_balance_row(id=2, is_archived=False),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(balance_id=1, amount=Decimal("-100"), executed_at=custom_date),
            make_ledger_row(balance_id=2, amount=Decimal("100"), executed_at=custom_date),
        ]

        await LedgerService._transfer(
            uow=uow,
            payload=RecordTransferPayload(
                operation_type=OperationTypeEnum.TRANSFER,
                from_balance_id=1,
                to_balance_id=2,
                amount=Decimal("100"),
                currency_ticker="USD",
                executed_at=custom_date,
            ),
        )

        first_call = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        second_call = uow.ledgers.add_one.await_args_list[1].kwargs["data"]
        assert first_call["executed_at"] == custom_date
        assert second_call["executed_at"] == custom_date


class TestTrade:
    async def test_creates_two_legs_on_the_same_balance_sharing_one_operation_id(
        self, uow
    ):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.side_effect = [
            make_currency_row(ticker="USD"),
            make_currency_row(ticker="AAPL", currency_type="stock"),
        ]
        uow.balances.get_name_by_id.return_value = "Broker"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(
                balance_id=1, currency_ticker="USD", amount=Decimal("-1000")
            ),
            make_ledger_row(
                balance_id=1, currency_ticker="AAPL", amount=Decimal("5.2")
            ),
        ]

        result = await LedgerService._trade(
            uow=uow,
            payload=RecordTradePayload(
                operation_type=OperationTypeEnum.TRADE,
                balance_id=1,
                spend_amount=Decimal("-1000"),
                spend_currency_ticker="USD",
                receive_amount=Decimal("5.2"),
                receive_currency_ticker="AAPL",
            ),
        )

        assert uow.ledgers.add_one.await_count == 2
        spend_call = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        receive_call = uow.ledgers.add_one.await_args_list[1].kwargs["data"]

        assert spend_call["balance_id"] == 1
        assert spend_call["currency_ticker"] == "USD"
        assert spend_call["amount"] == Decimal("-1000")
        assert receive_call["balance_id"] == 1
        assert receive_call["currency_ticker"] == "AAPL"
        assert receive_call["amount"] == Decimal("5.2")
        assert spend_call["operation_id"] == receive_call["operation_id"]
        assert spend_call["operation_type"] == OperationTypeEnum.TRADE
        assert len(result.items) == 2

    async def test_raises_not_found_when_balance_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Broker"

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService._trade(
                uow=uow,
                payload=RecordTradePayload(
                    operation_type=OperationTypeEnum.TRADE,
                    balance_id=999,
                    spend_amount=Decimal("-1000"),
                    spend_currency_ticker="USD",
                    receive_amount=Decimal("5.2"),
                    receive_currency_ticker="AAPL",
                ),
            )

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND

    async def test_fee_leg_shares_the_trade_operation_id(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.side_effect = [
            make_currency_row(ticker="USD"),
            make_currency_row(ticker="AAPL", currency_type="stock"),
            make_currency_row(ticker="USD"),
        ]
        uow.balances.get_name_by_id.return_value = "Broker"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(
                balance_id=1, currency_ticker="USD", amount=Decimal("-1000")
            ),
            make_ledger_row(
                balance_id=1, currency_ticker="AAPL", amount=Decimal("5.2")
            ),
            make_ledger_row(
                balance_id=1,
                currency_ticker="USD",
                amount=Decimal("-1"),
                operation_type=OperationTypeEnum.FEE,
            ),
        ]

        await LedgerService._trade(
            uow=uow,
            payload=RecordTradePayload(
                operation_type=OperationTypeEnum.TRADE,
                balance_id=1,
                spend_amount=Decimal("-1000"),
                spend_currency_ticker="USD",
                receive_amount=Decimal("5.2"),
                receive_currency_ticker="AAPL",
                fee_amount=Decimal("-1"),
                fee_currency_ticker="USD",
            ),
        )

        assert uow.ledgers.add_one.await_count == 3
        spend_leg = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        fee_leg = uow.ledgers.add_one.await_args_list[2].kwargs["data"]

        assert fee_leg["balance_id"] == 1
        assert fee_leg["amount"] == Decimal("-1")
        assert fee_leg["operation_type"] == OperationTypeEnum.FEE
        assert fee_leg["operation_id"] == spend_leg["operation_id"]

    async def test_propagates_executed_at_to_both_legs(self, uow):
        custom_date = datetime(2026, 1, 15, tzinfo=timezone.utc)
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.side_effect = [
            make_currency_row(ticker="USD"),
            make_currency_row(ticker="AAPL", currency_type="stock"),
        ]
        uow.balances.get_name_by_id.return_value = "Broker"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(
                balance_id=1, currency_ticker="USD", amount=Decimal("-1000"), executed_at=custom_date
            ),
            make_ledger_row(
                balance_id=1, currency_ticker="AAPL", amount=Decimal("5.2"), executed_at=custom_date
            ),
        ]

        await LedgerService._trade(
            uow=uow,
            payload=RecordTradePayload(
                operation_type=OperationTypeEnum.TRADE,
                balance_id=1,
                spend_amount=Decimal("-1000"),
                spend_currency_ticker="USD",
                receive_amount=Decimal("5.2"),
                receive_currency_ticker="AAPL",
                executed_at=custom_date,
            ),
        )

        spend_call = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        receive_call = uow.ledgers.add_one.await_args_list[1].kwargs["data"]
        assert spend_call["executed_at"] == custom_date
        assert receive_call["executed_at"] == custom_date


class TestRecordOperation:
    """The single public entry point — router only ever calls this, never the
    private _record_single_leg_operation / _transfer / _trade directly."""

    async def test_dispatches_income_to_single_leg_operation(self, uow):
        payload = RecordSingleLegOperationPayload(
            operation_type=OperationTypeEnum.INCOME,
            balance_id=1,
            amount=Decimal("500"),
            currency_ticker="USD",
        )
        with patch.object(
            LedgerService, "_record_single_leg_operation", new=AsyncMock()
        ) as mocked:
            await LedgerService.record_operation(uow=uow, payload=payload)

        mocked.assert_awaited_once_with(uow=uow, payload=payload)

    async def test_dispatches_expense_to_single_leg_operation(self, uow):
        payload = RecordSingleLegOperationPayload(
            operation_type=OperationTypeEnum.EXPENSE,
            balance_id=1,
            amount=Decimal("-40"),
            currency_ticker="USD",
        )
        with patch.object(
            LedgerService, "_record_single_leg_operation", new=AsyncMock()
        ) as mocked:
            await LedgerService.record_operation(uow=uow, payload=payload)

        mocked.assert_awaited_once_with(uow=uow, payload=payload)

    async def test_dispatches_fee_to_single_leg_operation(self, uow):
        payload = RecordSingleLegOperationPayload(
            operation_type=OperationTypeEnum.FEE,
            balance_id=1,
            amount=Decimal("-2.5"),
            currency_ticker="USD",
        )
        with patch.object(
            LedgerService, "_record_single_leg_operation", new=AsyncMock()
        ) as mocked:
            await LedgerService.record_operation(uow=uow, payload=payload)

        mocked.assert_awaited_once_with(uow=uow, payload=payload)

    async def test_dispatches_transfer_to_transfer(self, uow):
        payload = RecordTransferPayload(
            operation_type=OperationTypeEnum.TRANSFER,
            from_balance_id=1,
            to_balance_id=2,
            amount=Decimal("100"),
            currency_ticker="USD",
        )
        with patch.object(LedgerService, "_transfer", new=AsyncMock()) as mocked:
            await LedgerService.record_operation(uow=uow, payload=payload)

        mocked.assert_awaited_once_with(uow=uow, payload=payload)

    async def test_dispatches_trade_to_trade(self, uow):
        payload = RecordTradePayload(
            operation_type=OperationTypeEnum.TRADE,
            balance_id=1,
            spend_amount=Decimal("-1000"),
            spend_currency_ticker="USD",
            receive_amount=Decimal("5.2"),
            receive_currency_ticker="AAPL",
        )
        with patch.object(LedgerService, "_trade", new=AsyncMock()) as mocked:
            await LedgerService.record_operation(uow=uow, payload=payload)

        mocked.assert_awaited_once_with(uow=uow, payload=payload)


class TestUpdateOperationById:
    async def test_updates_ledger_entry(self, uow):
        uow.ledgers.edit_one.return_value = make_ledger_row(id=1, note="Corrected")

        result = await LedgerService.update_ledger_by_id(
            uow=uow, ledger_id=1, ledger_data=LedgerUpdateSchema(note="Corrected")
        )

        assert result.note == "Corrected"

    async def test_raises_not_found_when_missing(self, uow):
        uow.ledgers.edit_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService.update_ledger_by_id(
                uow=uow, ledger_id=999, ledger_data=LedgerUpdateSchema(note="X")
            )

        assert exc_info.value.message == Messages.LEDGER_ENTRY_NOT_FOUND


class TestDeleteOperationById:
    """A Ledger row deleted in isolation would either orphan its sibling leg
    (transfer/trade — money "arrives from nowhere"/"leaves to nowhere") or, when
    operation_id is None (a standalone income/expense/fee), has no siblings at
    all. delete_operation_by_id must therefore delete every row sharing the same
    operation_id together — or, when operation_id is None, just the one row."""

    async def test_deletes_single_row_when_operation_id_is_none(self, uow):
        # a standalone income/expense/fee recorded directly has no operation_id —
        # nothing to group it with, so deleting it must not touch any other row
        entry = make_ledger_row(id=1, operation_id=None)
        uow.ledgers.find_one_or_none.return_value = entry

        await LedgerService.delete_operation_by_id(uow=uow, ledger_id=1)

        uow.ledgers.delete_one.assert_awaited_once_with(_id=1)
        uow.ledgers.find_all.assert_not_called()

    async def test_deletes_both_legs_of_a_transfer(self, uow):
        shared_id = uuid4()
        entry = make_ledger_row(id=1, operation_id=shared_id)
        sibling = make_ledger_row(id=2, operation_id=shared_id)
        uow.ledgers.find_one_or_none.return_value = entry
        uow.ledgers.find_all.return_value = [entry, sibling]

        await LedgerService.delete_operation_by_id(uow=uow, ledger_id=1)

        uow.ledgers.find_all.assert_awaited_once_with(operation_id=shared_id)
        assert uow.ledgers.delete_one.await_count == 2
        deleted_ids = {call.kwargs["_id"] for call in uow.ledgers.delete_one.await_args_list}
        assert deleted_ids == {1, 2}

    async def test_deletes_all_three_legs_of_a_trade_with_fee(self, uow):
        shared_id = uuid4()
        legs = [
            make_ledger_row(id=1, operation_id=shared_id),
            make_ledger_row(id=2, operation_id=shared_id),
            make_ledger_row(id=3, operation_id=shared_id),
        ]
        uow.ledgers.find_one_or_none.return_value = legs[0]
        uow.ledgers.find_all.return_value = legs

        # deleting any one leg — not just the first — must delete the whole group
        await LedgerService.delete_operation_by_id(uow=uow, ledger_id=2)

        assert uow.ledgers.delete_one.await_count == 3
        deleted_ids = {call.kwargs["_id"] for call in uow.ledgers.delete_one.await_args_list}
        assert deleted_ids == {1, 2, 3}

    async def test_raises_not_found_when_missing(self, uow):
        uow.ledgers.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService.delete_operation_by_id(uow=uow, ledger_id=999)

        assert exc_info.value.message == Messages.LEDGER_ENTRY_NOT_FOUND
        uow.ledgers.delete_one.assert_not_called()
