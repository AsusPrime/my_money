from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from src.core.exceptions.exceptions import ConflictError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.enums.enums import OperationTypeEnum
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


class TestTransfer:
    async def test_creates_two_legs_sharing_one_operation_id(self, uow):
        uow.balances.find_one_or_none.side_effect = [
            make_balance_row(id=1, is_archived=False),
            make_balance_row(id=2, is_archived=False),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"
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
