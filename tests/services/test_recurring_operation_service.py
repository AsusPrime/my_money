from datetime import datetime
from datetime import timezone
from decimal import Decimal

import pytest

from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import BadRequestError
from src.core.exceptions.exceptions import ConflictError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.enums.enums import AmountModeEnum
from src.enums.enums import OperationTypeEnum
from src.enums.enums import RecurrenceIntervalEnum
from src.schemas.recurring_operation import RecurringOperationCreateSchema
from src.schemas.recurring_operation import RecurringOperationUpdateSchema
from src.services.recurring_operation_service import RecurringOperationService
from tests.services.conftest import make_account_row
from tests.services.conftest import make_balance_row
from tests.services.conftest import make_currency_row
from tests.services.conftest import make_ledger_row
from tests.services.conftest import make_recurring_operation_row


class TestGetAllRecurringOperations:
    async def test_returns_all_when_no_balance_id_given(self, uow):
        uow.recurring_operations.find_all.return_value = [
            make_recurring_operation_row(id=1),
            make_recurring_operation_row(id=2),
        ]

        result = await RecurringOperationService.get_all_recurring_operations(uow=uow)

        assert [r.id for r in result.items] == [1, 2]
        uow.recurring_operations.find_all.assert_awaited_once_with()

    async def test_returns_empty_list(self, uow):
        uow.recurring_operations.find_all.return_value = []

        result = await RecurringOperationService.get_all_recurring_operations(uow=uow)

        assert result.items == []

    async def test_filters_by_balance_id_when_given(self, uow):
        uow.recurring_operations.find_all.return_value = [
            make_recurring_operation_row(id=1, balance_id=2)
        ]

        result = await RecurringOperationService.get_all_recurring_operations(
            uow=uow, balance_id=2
        )

        assert [r.id for r in result.items] == [1]
        uow.recurring_operations.find_all.assert_awaited_once_with(balance_id=2)


class TestGetRecurringOperationById:
    async def test_returns_when_found(self, uow):
        uow.recurring_operations.find_one_or_none.return_value = make_recurring_operation_row(
            id=1
        )

        result = await RecurringOperationService.get_recurring_operation_by_id(
            uow=uow, recurring_operation_id=1
        )

        assert result.id == 1

    async def test_raises_not_found_when_missing(self, uow):
        uow.recurring_operations.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await RecurringOperationService.get_recurring_operation_by_id(
                uow=uow, recurring_operation_id=999
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_NOT_FOUND


class TestCreateRecurringOperation:
    def _payload(self, **overrides):
        defaults = dict(
            operation_type=OperationTypeEnum.INCOME,
            balance_id=1,
            currency_ticker="USD",
            amount_mode=AmountModeEnum.FIXED,
            amount_value=Decimal("50"),
            interval=RecurrenceIntervalEnum.MONTHLY,
            day_of_month=1,
        )
        defaults.update(overrides)
        return RecurringOperationCreateSchema(**defaults)

    async def test_creates_when_balance_and_currency_exist(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.recurring_operations.add_one.return_value = make_recurring_operation_row(id=1)

        result = await RecurringOperationService.create_recurring_operation(
            uow=uow, data=self._payload()
        )

        assert result.id == 1
        uow.recurring_operations.add_one.assert_awaited_once()

    async def test_raises_not_found_when_balance_missing(self, uow):
        uow.balances.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow, data=self._payload()
            )

        assert exc_info.value.message == Messages.BALANCE_NOT_FOUND
        uow.recurring_operations.add_one.assert_not_called()

    @pytest.mark.parametrize(
        "operation_type", [OperationTypeEnum.INCOME, OperationTypeEnum.EXPENSE, OperationTypeEnum.FEE]
    )
    async def test_accepts_single_leg_operation_types(self, uow, operation_type):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.recurring_operations.add_one.return_value = make_recurring_operation_row(id=1)

        await RecurringOperationService.create_recurring_operation(
            uow=uow, data=self._payload(operation_type=operation_type)
        )

        uow.recurring_operations.add_one.assert_awaited_once()

    @pytest.mark.parametrize(
        "operation_type", [OperationTypeEnum.TRANSFER, OperationTypeEnum.TRADE]
    )
    async def test_rejects_transfer_and_trade(self, uow, operation_type):
        with pytest.raises(BadRequestError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow, data=self._payload(operation_type=operation_type)
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_TYPE_NOT_SUPPORTED
        uow.recurring_operations.add_one.assert_not_called()

    async def test_raises_conflict_when_balance_is_archived(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=True)

        with pytest.raises(ConflictError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow, data=self._payload()
            )

        assert exc_info.value.message == Messages.BALANCE_IS_ARCHIVED

    async def test_raises_not_found_when_currency_missing(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow, data=self._payload()
            )

        assert exc_info.value.message == Messages.CURRENCY_NOT_FOUND

    async def test_raises_add_record_error_when_insert_fails(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.recurring_operations.add_one.return_value = None

        with pytest.raises(AddRecordError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow, data=self._payload()
            )

        assert exc_info.value.message == Messages.ERROR_FILLED_TO_ADD_NEW_RECURRING_OPERATION

    async def test_daily_accepts_no_schedule_fields(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.recurring_operations.add_one.return_value = make_recurring_operation_row(id=1)

        await RecurringOperationService.create_recurring_operation(
            uow=uow,
            data=self._payload(interval=RecurrenceIntervalEnum.DAILY, day_of_month=None),
        )

        uow.recurring_operations.add_one.assert_awaited_once()

    async def test_daily_rejects_day_of_month(self, uow):
        with pytest.raises(BadRequestError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow,
                data=self._payload(interval=RecurrenceIntervalEnum.DAILY, day_of_month=1),
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_INVALID_SCHEDULE

    async def test_weekly_requires_day_of_week(self, uow):
        with pytest.raises(BadRequestError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow,
                data=self._payload(interval=RecurrenceIntervalEnum.WEEKLY, day_of_month=None),
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_INVALID_SCHEDULE

    async def test_weekly_accepts_valid_day_of_week(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.recurring_operations.add_one.return_value = make_recurring_operation_row(id=1)

        await RecurringOperationService.create_recurring_operation(
            uow=uow,
            data=self._payload(
                interval=RecurrenceIntervalEnum.WEEKLY, day_of_month=None, day_of_week=0
            ),
        )

        uow.recurring_operations.add_one.assert_awaited_once()

    async def test_weekly_rejects_day_of_week_out_of_range(self, uow):
        with pytest.raises(BadRequestError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow,
                data=self._payload(
                    interval=RecurrenceIntervalEnum.WEEKLY, day_of_month=None, day_of_week=7
                ),
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_INVALID_SCHEDULE

    async def test_monthly_requires_day_of_month(self, uow):
        with pytest.raises(BadRequestError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow,
                data=self._payload(interval=RecurrenceIntervalEnum.MONTHLY, day_of_month=None),
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_INVALID_SCHEDULE

    @pytest.mark.parametrize("day_of_month", [1, 15, 31, -1, -2, -31])
    async def test_monthly_accepts_valid_day_of_month(self, uow, day_of_month):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.recurring_operations.add_one.return_value = make_recurring_operation_row(id=1)

        await RecurringOperationService.create_recurring_operation(
            uow=uow, data=self._payload(day_of_month=day_of_month)
        )

        uow.recurring_operations.add_one.assert_awaited_once()

    @pytest.mark.parametrize("day_of_month", [0, 32, -32])
    async def test_monthly_rejects_invalid_day_of_month(self, uow, day_of_month):
        with pytest.raises(BadRequestError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow, data=self._payload(day_of_month=day_of_month)
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_INVALID_SCHEDULE

    async def test_yearly_requires_month_and_day_of_month(self, uow):
        with pytest.raises(BadRequestError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow,
                data=self._payload(interval=RecurrenceIntervalEnum.YEARLY, day_of_month=None),
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_INVALID_SCHEDULE

    async def test_yearly_accepts_valid_month_and_day(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.recurring_operations.add_one.return_value = make_recurring_operation_row(id=1)

        await RecurringOperationService.create_recurring_operation(
            uow=uow,
            data=self._payload(interval=RecurrenceIntervalEnum.YEARLY, day_of_month=25, month=12),
        )

        uow.recurring_operations.add_one.assert_awaited_once()

    async def test_yearly_accepts_last_day_of_february_even_in_leap_only_case(self, uow):
        uow.balances.find_one_or_none.return_value = make_balance_row(id=1, is_archived=False)
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.recurring_operations.add_one.return_value = make_recurring_operation_row(id=1)

        # -29 in February only ever occurs on leap years -> allowed, just rare
        await RecurringOperationService.create_recurring_operation(
            uow=uow,
            data=self._payload(interval=RecurrenceIntervalEnum.YEARLY, day_of_month=-29, month=2),
        )

        uow.recurring_operations.add_one.assert_awaited_once()

    async def test_yearly_rejects_day_of_month_that_can_never_occur_in_the_given_month(self, uow):
        # -30 in February can never occur - February has at most 29 days
        with pytest.raises(BadRequestError) as exc_info:
            await RecurringOperationService.create_recurring_operation(
                uow=uow,
                data=self._payload(
                    interval=RecurrenceIntervalEnum.YEARLY, day_of_month=-30, month=2
                ),
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_INVALID_SCHEDULE


class TestUpdateRecurringOperationById:
    async def test_updates_when_found(self, uow):
        uow.recurring_operations.edit_one.return_value = make_recurring_operation_row(
            id=1, is_active=False
        )

        result = await RecurringOperationService.update_recurring_operation_by_id(
            uow=uow,
            recurring_operation_id=1,
            data=RecurringOperationUpdateSchema(is_active=False),
        )

        assert result.is_active is False

    async def test_raises_not_found_when_missing(self, uow):
        uow.recurring_operations.edit_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await RecurringOperationService.update_recurring_operation_by_id(
                uow=uow,
                recurring_operation_id=999,
                data=RecurringOperationUpdateSchema(is_active=False),
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_NOT_FOUND

    async def test_update_schema_has_no_schedule_fields(self):
        # rescheduling mid-cycle is ambiguous (e.g. already fired today at
        # 15:00, now moved to 15:30 — does it fire again today?), so the
        # schedule can only be set at creation; changing it means delete + create
        schedule_fields = {"interval", "day_of_month", "day_of_week", "month", "hour", "minute"}
        assert schedule_fields.isdisjoint(RecurringOperationUpdateSchema.model_fields)


class TestDeleteRecurringOperationById:
    async def test_deletes_when_found(self, uow):
        uow.recurring_operations.delete_one.return_value = make_recurring_operation_row(id=1)

        await RecurringOperationService.delete_recurring_operation_by_id(
            uow=uow, recurring_operation_id=1
        )

        uow.recurring_operations.delete_one.assert_awaited_once_with(_id=1)

    async def test_raises_not_found_when_missing(self, uow):
        uow.recurring_operations.delete_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await RecurringOperationService.delete_recurring_operation_by_id(
                uow=uow, recurring_operation_id=999
            )

        assert exc_info.value.message == Messages.RECURRING_OPERATION_NOT_FOUND


class TestRun:
    async def test_records_a_ledger_operation_with_fixed_amount(self, uow):
        row = make_recurring_operation_row(
            id=1,
            operation_type=OperationTypeEnum.INCOME,
            balance_id=1,
            currency_ticker="USD",
            amount_mode=AmountModeEnum.FIXED,
            amount_value=Decimal("50"),
            interval=RecurrenceIntervalEnum.MONTHLY,
        )
        uow.recurring_operations.find_one_or_none.return_value = row
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, account_id=1, is_archived=False
        )
        uow.accounts.find_one_or_none.return_value = make_account_row(
            id=1, base_currency_ticker="USD"
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("1000")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1, amount=Decimal("50"))

        await RecurringOperationService.run(uow=uow, recurring_operation_id=1)

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["amount"] == Decimal("50")
        assert kwargs["data"]["balance_id"] == 1
        assert row.last_run_at is not None

    async def test_records_a_ledger_operation_with_percent_of_balance_amount(self, uow):
        row = make_recurring_operation_row(
            id=1,
            balance_id=1,
            currency_ticker="USD",
            amount_mode=AmountModeEnum.PERCENT_OF_BALANCE,
            amount_value=Decimal("2"),
            interval=RecurrenceIntervalEnum.DAILY,
        )
        uow.recurring_operations.find_one_or_none.return_value = row
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, account_id=1, is_archived=False
        )
        uow.accounts.find_one_or_none.return_value = make_account_row(
            id=1, base_currency_ticker="USD"
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("1000")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1, amount=Decimal("20"))

        await RecurringOperationService.run(uow=uow, recurring_operation_id=1)

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["amount"] == Decimal("20")

    async def test_uses_occurred_at_as_the_ledger_executed_at_when_given(self, uow):
        # catch-up backfill — the entry should be backdated to when it
        # conceptually should have posted, not to whenever we actually ran it
        row = make_recurring_operation_row(id=1, interval=RecurrenceIntervalEnum.MONTHLY)
        uow.recurring_operations.find_one_or_none.return_value = row
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, account_id=1, is_archived=False
        )
        uow.accounts.find_one_or_none.return_value = make_account_row(
            id=1, base_currency_ticker="USD"
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("1000")}
        uow.ledgers.add_one.return_value = make_ledger_row(balance_id=1)
        occurred_at = datetime(2026, 6, 1, tzinfo=timezone.utc)

        await RecurringOperationService.run(
            uow=uow, recurring_operation_id=1, occurred_at=occurred_at
        )

        _, kwargs = uow.ledgers.add_one.await_args
        assert kwargs["data"]["executed_at"] == occurred_at
        assert row.last_run_at == occurred_at

    async def test_does_nothing_when_recurring_operation_is_missing(self, uow):
        uow.recurring_operations.find_one_or_none.return_value = None

        await RecurringOperationService.run(uow=uow, recurring_operation_id=999)

        uow.ledgers.add_one.assert_not_called()

    async def test_does_nothing_when_recurring_operation_is_inactive(self, uow):
        row = make_recurring_operation_row(id=1, is_active=False)
        uow.recurring_operations.find_one_or_none.return_value = row

        await RecurringOperationService.run(uow=uow, recurring_operation_id=1)

        uow.ledgers.add_one.assert_not_called()
        assert row.last_run_at is None

    async def test_marks_ran_even_when_recording_fails(self, uow):
        # e.g. an expense that exceeds current funds — the cycle is skipped,
        # not retried forever
        row = make_recurring_operation_row(
            id=1,
            operation_type=OperationTypeEnum.EXPENSE,
            balance_id=1,
            currency_ticker="USD",
            amount_mode=AmountModeEnum.FIXED,
            amount_value=Decimal("500"),
            interval=RecurrenceIntervalEnum.DAILY,
        )
        uow.recurring_operations.find_one_or_none.return_value = row
        uow.balances.find_one_or_none.return_value = make_balance_row(
            id=1, account_id=1, is_archived=False
        )
        uow.currencies.find_one_or_none.return_value = make_currency_row(ticker="USD")
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("10")}

        await RecurringOperationService.run(uow=uow, recurring_operation_id=1)

        uow.ledgers.add_one.assert_not_called()
        assert row.last_run_at is not None
