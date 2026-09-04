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
from src.enums.enums import LedgerReportGroupByEnum
from src.enums.enums import LedgerReportMetricEnum
from src.enums.enums import NetWorthBucketEnum
from src.enums.enums import OperationTypeEnum
from src.schemas.ledger import LedgerUpdateSchema
from src.schemas.ledger import RecordSingleLegOperationPayload
from src.schemas.ledger import RecordTradePayload
from src.schemas.ledger import RecordTransferPayload
from src.services.ledger_service import LedgerService
from tests.services.conftest import make_account_row
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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
        uow.accounts.find_one_or_none.return_value = make_account_row()
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


class TestRecordSingleLegOperationBaseCurrencyRate:
    async def test_passes_explicit_base_currency_rate_through_to_insert(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1, amount=Decimal("500"), base_currency_rate=Decimal("39.2")
        )

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("500"),
                currency_ticker="USD",
                base_currency_rate=Decimal("39.2"),
            ),
        )

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["base_currency_rate"] == Decimal("39.2")

    async def test_defaults_to_none_when_not_given(self, uow):
        # no rate to auto-derive it from — must stay None, never guessed
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.accounts.find_one_or_none.return_value = make_account_row()
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
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

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["base_currency_rate"] is None


class TestRecordSingleLegOperationAutoResolveBaseCurrencyRate:
    """A standalone single-leg operation in a currency other than the account's
    base currency has no paired leg to derive a rate from, so the service asks
    ExchangeRateService for a historical one. Transfer/trade legs call with
    resolve_base_currency_rate=False and skip this entirely, since their cost
    basis is already derivable from the paired leg amounts."""

    async def test_fetches_rate_when_currency_differs_from_account_base_currency(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, account_id=1, is_archived=False)
        uow.accounts.find_one_or_none.return_value = make_account_row(id=1, base_currency_ticker="USD")
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="EUR")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"EUR": Decimal("0")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1, currency_ticker="EUR", amount=Decimal("100"), base_currency_rate=Decimal("1.08")
        )
        exchange_rate_service = AsyncMock()
        exchange_rate_service.get_historical_rate.return_value = Decimal("1.08")

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("100"),
                currency_ticker="EUR",
            ),
            exchange_rate_service=exchange_rate_service,
        )

        exchange_rate_service.get_historical_rate.assert_awaited_once()
        _, rate_kwargs = exchange_rate_service.get_historical_rate.await_args
        assert rate_kwargs["currency_ticker"] == "EUR"
        assert rate_kwargs["base_currency_ticker"] == "USD"
        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["base_currency_rate"] == Decimal("1.08")

    async def test_does_not_fetch_rate_when_currency_matches_account_base_currency(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, account_id=1, is_archived=False)
        uow.accounts.find_one_or_none.return_value = make_account_row(id=1, base_currency_ticker="USD")
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("0")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1, amount=Decimal("100"))
        exchange_rate_service = AsyncMock()

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("100"),
                currency_ticker="USD",
            ),
            exchange_rate_service=exchange_rate_service,
        )

        exchange_rate_service.get_historical_rate.assert_not_awaited()

    async def test_manual_rate_takes_priority_over_auto_fetch(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, account_id=1, is_archived=False)
        uow.accounts.find_one_or_none.return_value = make_account_row(id=1, base_currency_ticker="USD")
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="EUR")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"EUR": Decimal("0")}
        uow.ledgers.add_one.return_value = make_ledger_row(
            balance_id=1, currency_ticker="EUR", amount=Decimal("100"), base_currency_rate=Decimal("1.5")
        )
        exchange_rate_service = AsyncMock()

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("100"),
                currency_ticker="EUR",
                base_currency_rate=Decimal("1.5"),
            ),
            exchange_rate_service=exchange_rate_service,
        )

        exchange_rate_service.get_historical_rate.assert_not_awaited()
        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["base_currency_rate"] == Decimal("1.5")

    async def test_skips_resolution_entirely_when_disabled(self, uow):
        # this is how _transfer/_trade call each leg — cost basis is already
        # derivable from the paired leg amounts, so no fetch should happen
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, account_id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="EUR")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"EUR": Decimal("0")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1, currency_ticker="EUR", amount=Decimal("100"))
        exchange_rate_service = AsyncMock()

        await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum.INCOME,
                balance_id=1,
                amount=Decimal("100"),
                currency_ticker="EUR",
            ),
            exchange_rate_service=exchange_rate_service,
            resolve_base_currency_rate=False,
        )

        exchange_rate_service.get_historical_rate.assert_not_awaited()
        uow.accounts.find_one_or_none.assert_not_awaited()
        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["base_currency_rate"] is None


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

    async def test_propagates_base_currency_rate_to_both_legs(self, uow):
        uow.balances.find_one_or_none.side_effect = [
            make_balance_row(id=1, is_archived=False),
            make_balance_row(id=2, is_archived=False),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.balances.get_name_by_id.return_value = "Card"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(balance_id=1, amount=Decimal("-100"), base_currency_rate=Decimal("39.2")),
            make_ledger_row(balance_id=2, amount=Decimal("100"), base_currency_rate=Decimal("39.2")),
        ]

        await LedgerService._transfer(
            uow=uow,
            payload=RecordTransferPayload(
                operation_type=OperationTypeEnum.TRANSFER,
                from_balance_id=1,
                to_balance_id=2,
                amount=Decimal("100"),
                currency_ticker="USD",
                base_currency_rate=Decimal("39.2"),
            ),
        )

        first_call = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        second_call = uow.ledgers.add_one.await_args_list[1].kwargs["data"]
        assert first_call["base_currency_rate"] == Decimal("39.2")
        assert second_call["base_currency_rate"] == Decimal("39.2")


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

    async def test_propagates_base_currency_rate_to_both_legs(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.side_effect = [
            make_currency_row(ticker="USD"),
            make_currency_row(ticker="AAPL", currency_type="stock"),
        ]
        uow.balances.get_name_by_id.return_value = "Broker"
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10000")}
        uow.ledgers.add_one.side_effect = [
            make_ledger_row(
                balance_id=1, currency_ticker="USD", amount=Decimal("-1000"), base_currency_rate=Decimal("39.2")
            ),
            make_ledger_row(
                balance_id=1, currency_ticker="AAPL", amount=Decimal("5.2"), base_currency_rate=Decimal("39.2")
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
                base_currency_rate=Decimal("39.2"),
            ),
        )

        spend_call = uow.ledgers.add_one.await_args_list[0].kwargs["data"]
        receive_call = uow.ledgers.add_one.await_args_list[1].kwargs["data"]
        assert spend_call["base_currency_rate"] == Decimal("39.2")
        assert receive_call["base_currency_rate"] == Decimal("39.2")


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
    async def test_update_schema_has_no_amount_affecting_fields(self):
        # amount/currency/rate changes need sign re-normalization, a funds
        # re-check, and (for transfer/trade) sibling-leg consistency — none of
        # which a raw field patch can guarantee, so they go through
        # replace_operation instead, never through this schema
        unsafe_fields = {"amount", "currency_ticker", "base_currency_rate", "operation_type"}
        assert unsafe_fields.isdisjoint(LedgerUpdateSchema.model_fields)

    async def test_raises_bad_request_when_no_fields_are_given(self, uow):
        # an all-unset (or all-unknown-field) body would otherwise reach the
        # repository as an empty SET clause and blow up as a raw DB error
        with pytest.raises(BadRequestError) as exc_info:
            await LedgerService.update_ledger_by_id(
                uow=uow, ledger_id=1, ledger_data=LedgerUpdateSchema()
            )

        assert exc_info.value.message == Messages.LEDGER_UPDATE_NO_FIELDS
        uow.ledgers.edit_one.assert_not_called()

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


class TestGetOperationGroupByLedgerId:
    """A transfer/trade leg's sibling(s) can live on a different balance, so
    the group can't be reconstructed from the balance-scoped ledger list —
    this is what the edit UI uses to pre-fill the from/to/fee legs."""

    async def test_returns_only_itself_when_operation_id_is_none(self, uow):
        entry = make_ledger_row(id=1, operation_id=None)
        uow.ledgers.find_one_or_none.return_value = entry

        result = await LedgerService.get_operation_group_by_ledger_id(uow=uow, ledger_id=1)

        assert [item.id for item in result.items] == [1]
        uow.ledgers.find_all.assert_not_called()

    async def test_returns_every_leg_sharing_the_operation_id(self, uow):
        shared_id = uuid4()
        entry = make_ledger_row(id=1, operation_id=shared_id, balance_id=1)
        sibling = make_ledger_row(id=2, operation_id=shared_id, balance_id=2)
        uow.ledgers.find_one_or_none.return_value = entry
        uow.ledgers.find_all.return_value = [entry, sibling]

        result = await LedgerService.get_operation_group_by_ledger_id(uow=uow, ledger_id=1)

        uow.ledgers.find_all.assert_awaited_once_with(operation_id=shared_id)
        assert {item.id for item in result.items} == {1, 2}

    async def test_raises_not_found_when_missing(self, uow):
        uow.ledgers.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService.get_operation_group_by_ledger_id(uow=uow, ledger_id=999)

        assert exc_info.value.message == Messages.LEDGER_ENTRY_NOT_FOUND


class TestReplaceOperation:
    """Editing amount/currency/legs reuses record_operation's already-correct
    sign/funds/rate logic rather than duplicating it — delete the old leg(s),
    then record the new payload fresh, both inside the same transaction."""

    async def test_deletes_the_old_operation_then_records_the_new_payload(self, uow):
        payload = RecordSingleLegOperationPayload(
            operation_type=OperationTypeEnum.EXPENSE,
            balance_id=1,
            amount=Decimal("60"),
            currency_ticker="USD",
        )
        with (
            patch.object(
                LedgerService, "delete_operation_by_id", new=AsyncMock()
            ) as mocked_delete,
            patch.object(
                LedgerService, "record_operation", new=AsyncMock()
            ) as mocked_record,
        ):
            await LedgerService.replace_operation(uow=uow, ledger_id=1, payload=payload)

        mocked_delete.assert_awaited_once_with(uow=uow, ledger_id=1)
        mocked_record.assert_awaited_once_with(uow=uow, payload=payload)

    async def test_propagates_not_found_when_the_operation_is_missing(self, uow):
        uow.ledgers.find_one_or_none.return_value = None
        payload = RecordSingleLegOperationPayload(
            operation_type=OperationTypeEnum.EXPENSE,
            balance_id=1,
            amount=Decimal("60"),
            currency_ticker="USD",
        )

        with pytest.raises(NotFoundError) as exc_info:
            await LedgerService.replace_operation(uow=uow, ledger_id=999, payload=payload)

        assert exc_info.value.message == Messages.LEDGER_ENTRY_NOT_FOUND
        uow.ledgers.add_one.assert_not_called()
        uow.ledgers.delete_one.assert_not_called()


class TestGetReport:
    async def test_formats_plain_string_groups_as_is(self, uow):
        uow.ledgers.aggregate.return_value = [
            ("Salary", Decimal("1000")),
            ("Food", Decimal("-30")),
        ]

        result = await LedgerService.get_report(
            uow=uow,
            group_by=LedgerReportGroupByEnum.CATEGORY,
            metric=LedgerReportMetricEnum.SUM,
        )

        assert [(i.group, i.value) for i in result.items] == [
            ("Salary", Decimal("1000")),
            ("Food", Decimal("-30")),
        ]

    async def test_formats_a_datetime_group_as_an_iso_date(self, uow):
        uow.ledgers.aggregate.return_value = [
            (datetime(2026, 1, 1, tzinfo=timezone.utc), Decimal("150")),
        ]

        result = await LedgerService.get_report(
            uow=uow,
            group_by=LedgerReportGroupByEnum.MONTH,
            metric=LedgerReportMetricEnum.SUM,
        )

        assert result.items[0].group == "2026-01-01"

    async def test_formats_an_enum_group_by_its_value(self, uow):
        uow.ledgers.aggregate.return_value = [
            (OperationTypeEnum.EXPENSE, Decimal("-40")),
        ]

        result = await LedgerService.get_report(
            uow=uow,
            group_by=LedgerReportGroupByEnum.OPERATION_TYPE,
            metric=LedgerReportMetricEnum.SUM,
        )

        assert result.items[0].group == "expense"

    async def test_treats_a_none_value_as_zero(self, uow):
        uow.ledgers.aggregate.return_value = [("Empty", None)]

        result = await LedgerService.get_report(
            uow=uow,
            group_by=LedgerReportGroupByEnum.CATEGORY,
            metric=LedgerReportMetricEnum.SUM,
        )

        assert result.items[0].value == Decimal("0")

    async def test_passes_filters_through_to_the_repository(self, uow):
        uow.ledgers.aggregate.return_value = []
        date_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_end = datetime(2026, 2, 1, tzinfo=timezone.utc)

        await LedgerService.get_report(
            uow=uow,
            group_by=LedgerReportGroupByEnum.CURRENCY_TICKER,
            metric=LedgerReportMetricEnum.NET_OF_FEES,
            date_start=date_start,
            date_end=date_end,
            operation_types=[OperationTypeEnum.EXPENSE],
            currency_ticker="USD",
            category_ids=[1],
            balance_ids=[2],
            account_id=3,
        )

        uow.ledgers.aggregate.assert_awaited_once_with(
            group_by=LedgerReportGroupByEnum.CURRENCY_TICKER,
            metric=LedgerReportMetricEnum.NET_OF_FEES,
            date_start=date_start,
            date_end=date_end,
            operation_types=[OperationTypeEnum.EXPENSE],
            currency_ticker="USD",
            category_ids=[1],
            balance_ids=[2],
            account_id=3,
        )


class TestGetOperationsByBalanceId:
    async def test_has_more_false_when_fewer_rows_than_limit(self, uow):
        uow.ledgers.find_all_by_balance_id.return_value = [
            make_ledger_row(id=1),
            make_ledger_row(id=2),
        ]

        result = await LedgerService.get_operations_by_balance_id(
            uow=uow, balance_id=1, limit=10, offset=0
        )

        assert [i.id for i in result.items] == [1, 2]
        assert result.has_more is False
        uow.ledgers.find_all_by_balance_id.assert_awaited_once_with(
            balance_id=1, limit=11, offset=0
        )

    async def test_has_more_true_and_trims_the_extra_probe_row(self, uow):
        uow.ledgers.find_all_by_balance_id.return_value = [
            make_ledger_row(id=1),
            make_ledger_row(id=2),
            make_ledger_row(id=3),
        ]

        result = await LedgerService.get_operations_by_balance_id(
            uow=uow, balance_id=1, limit=2, offset=0
        )

        assert [i.id for i in result.items] == [1, 2]
        assert result.has_more is True

    async def test_passes_offset_through_to_the_repository(self, uow):
        uow.ledgers.find_all_by_balance_id.return_value = []

        await LedgerService.get_operations_by_balance_id(
            uow=uow, balance_id=1, limit=10, offset=20
        )

        uow.ledgers.find_all_by_balance_id.assert_awaited_once_with(
            balance_id=1, limit=11, offset=20
        )


class TestGetNetWorth:
    """Cumulative running total converted into currency_ticker, one point per
    bucket, forward-filled across buckets with no activity. Deliberately
    resolved from each leg's already-stored base_currency_rate rather than
    re-fetching a historical rate — free providers turned out not to reliably
    have history going back far enough (see the method's own docstring)."""

    async def test_same_currency_legs_need_no_rate_lookup(self, uow):
        uow.ledgers.get_rows_for_net_worth.return_value = [
            (datetime(2026, 1, 5, tzinfo=timezone.utc), "UAH", Decimal("1000"), None, "UAH"),
            (datetime(2026, 1, 20, tzinfo=timezone.utc), "UAH", Decimal("-200"), None, "UAH"),
            (datetime(2026, 2, 10, tzinfo=timezone.utc), "UAH", Decimal("500"), None, "UAH"),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(
            ticker="UAH", decimal_places=2
        )
        exchange_rate_service = AsyncMock()

        result = await LedgerService.get_net_worth(
            uow=uow,
            currency_ticker="UAH",
            group_by=NetWorthBucketEnum.MONTH,
            date_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            date_end=datetime(2026, 2, 28, tzinfo=timezone.utc),
            exchange_rate_service=exchange_rate_service,
        )

        assert [(i.group, i.value) for i in result.items] == [
            ("2026-01-01", Decimal("800")),
            ("2026-02-01", Decimal("1300")),
        ]
        exchange_rate_service.get_current_rate.assert_not_awaited()

    async def test_uses_the_legs_own_stored_base_currency_rate_when_it_matches_the_target(
        self, uow
    ):
        uow.ledgers.get_rows_for_net_worth.return_value = [
            (
                datetime(2026, 1, 5, tzinfo=timezone.utc),
                "EUR",
                Decimal("100"),
                Decimal("43.5"),
                "UAH",
            ),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(
            ticker="UAH", decimal_places=2
        )
        exchange_rate_service = AsyncMock()

        result = await LedgerService.get_net_worth(
            uow=uow,
            currency_ticker="UAH",
            group_by=NetWorthBucketEnum.MONTH,
            date_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            date_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
            exchange_rate_service=exchange_rate_service,
        )

        assert result.items[0].value == Decimal("4350.0")
        exchange_rate_service.get_current_rate.assert_not_awaited()

    async def test_falls_back_to_a_live_rate_when_no_stored_rate_is_usable(self, uow):
        # a trade leg recorded without resolve_base_currency_rate — a real gap
        # seen in this app's own historical data (old BTC/USDT trade legs)
        uow.ledgers.get_rows_for_net_worth.return_value = [
            (
                datetime(2026, 1, 5, tzinfo=timezone.utc),
                "BTC",
                Decimal("0.01"),
                None,
                "UAH",
            ),
        ]
        uow.currencies.find_one_or_none.side_effect = [
            make_currency_row(ticker="UAH", decimal_places=2),
            make_currency_row(ticker="BTC", currency_type="crypto", decimal_places=8),
        ]
        exchange_rate_service = AsyncMock()
        exchange_rate_service.get_current_rate.return_value = Decimal("2500000")

        result = await LedgerService.get_net_worth(
            uow=uow,
            currency_ticker="UAH",
            group_by=NetWorthBucketEnum.MONTH,
            date_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            date_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
            exchange_rate_service=exchange_rate_service,
        )

        assert result.items[0].value == Decimal("25000.00")
        exchange_rate_service.get_current_rate.assert_awaited_once_with(
            currency_ticker="BTC", base_currency_ticker="UAH", currency_type="crypto"
        )

    async def test_forward_fills_buckets_with_no_activity(self, uow):
        uow.ledgers.get_rows_for_net_worth.return_value = [
            (datetime(2026, 1, 5, tzinfo=timezone.utc), "UAH", Decimal("1000"), None, "UAH"),
        ]
        uow.currencies.find_one_or_none.return_value = make_currency_row(
            ticker="UAH", decimal_places=2
        )
        exchange_rate_service = AsyncMock()

        result = await LedgerService.get_net_worth(
            uow=uow,
            currency_ticker="UAH",
            group_by=NetWorthBucketEnum.MONTH,
            date_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            date_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
            exchange_rate_service=exchange_rate_service,
        )

        assert [(i.group, i.value) for i in result.items] == [
            ("2026-01-01", Decimal("1000")),
            ("2026-02-01", Decimal("1000")),
            ("2026-03-01", Decimal("1000")),
        ]

    async def test_defaults_date_start_to_the_earliest_ledger_entry(self, uow):
        uow.ledgers.get_earliest_executed_at.return_value = datetime(
            2025, 11, 15, tzinfo=timezone.utc
        )
        uow.ledgers.get_rows_for_net_worth.return_value = []
        uow.currencies.find_one_or_none.return_value = make_currency_row(
            ticker="UAH", decimal_places=2
        )

        result = await LedgerService.get_net_worth(
            uow=uow,
            currency_ticker="UAH",
            group_by=NetWorthBucketEnum.MONTH,
            date_end=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )

        assert [i.group for i in result.items] == ["2025-11-01", "2025-12-01", "2026-01-01"]

    async def test_returns_empty_items_when_there_is_no_ledger_data_at_all(self, uow):
        uow.ledgers.get_earliest_executed_at.return_value = None

        result = await LedgerService.get_net_worth(
            uow=uow, currency_ticker="UAH", group_by=NetWorthBucketEnum.MONTH
        )

        assert result.items == []
        uow.ledgers.get_rows_for_net_worth.assert_not_awaited()
