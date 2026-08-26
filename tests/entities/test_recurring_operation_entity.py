from datetime import datetime
from datetime import timezone
from decimal import Decimal

import pytest
from apscheduler.triggers.cron import CronTrigger

from src.core.exceptions.exceptions import BadRequestError
from src.enums.enums import AmountModeEnum
from src.enums.enums import RecurrenceIntervalEnum
from src.entities.recurring_operation import RecurringOperationEntity
from src.utils.triggers.triggers import MonthEndOffsetTrigger
from tests.entities.conftest import make_currency_row
from tests.entities.conftest import make_recurring_operation_row


class TestResolveAmount:
    async def test_fixed_mode_returns_amount_value_as_is(self, uow):
        row = make_recurring_operation_row(
            amount_mode=AmountModeEnum.FIXED, amount_value=Decimal("50")
        )
        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)

        result = await entity.resolve_amount()

        assert result == Decimal("50")
        uow.ledgers.get_amounts_by_balance_id.assert_not_called()

    async def test_percent_of_balance_computes_from_current_balance(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"USD": Decimal("1000")}
        uow.currencies.find_one_or_none.return_value = make_currency_row(
            ticker="USD", decimal_places=2
        )
        row = make_recurring_operation_row(
            balance_id=1,
            currency_ticker="USD",
            amount_mode=AmountModeEnum.PERCENT_OF_BALANCE,
            amount_value=Decimal("2.5"),
        )
        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)

        result = await entity.resolve_amount()

        assert result == Decimal("25.00")
        uow.ledgers.get_amounts_by_balance_id.assert_awaited_once_with(balance_id=1)

    async def test_percent_of_balance_is_zero_when_currency_has_no_funds(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {}
        uow.currencies.find_one_or_none.return_value = make_currency_row(
            ticker="USD", decimal_places=2
        )
        row = make_recurring_operation_row(
            currency_ticker="USD",
            amount_mode=AmountModeEnum.PERCENT_OF_BALANCE,
            amount_value=Decimal("2.5"),
        )
        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)

        result = await entity.resolve_amount()

        assert result == Decimal("0.00")

    async def test_percent_of_balance_rounds_to_the_currency_decimal_places(self, uow):
        # the exact scenario reported: a 0.01% fee against a balance that
        # doesn't divide evenly produces a long decimal tail — must round to
        # what the currency can actually settle (2 places for UAH), not carry
        # the full 8-decimal ledger precision
        uow.ledgers.get_amounts_by_balance_id.return_value = {"UAH": Decimal("12199.9")}
        uow.currencies.find_one_or_none.return_value = make_currency_row(
            ticker="UAH", decimal_places=2
        )
        row = make_recurring_operation_row(
            currency_ticker="UAH",
            amount_mode=AmountModeEnum.PERCENT_OF_BALANCE,
            amount_value=Decimal("0.01"),
        )
        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)

        result = await entity.resolve_amount()

        assert result == Decimal("1.22")

    async def test_percent_of_balance_rounds_to_8_places_for_crypto(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {"BTC": Decimal("1.123456789")}
        uow.currencies.find_one_or_none.return_value = make_currency_row(
            ticker="BTC", currency_type="crypto", decimal_places=8
        )
        row = make_recurring_operation_row(
            currency_ticker="BTC",
            amount_mode=AmountModeEnum.PERCENT_OF_BALANCE,
            amount_value=Decimal("1"),
        )
        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)

        result = await entity.resolve_amount()

        assert result == Decimal("0.01123457")


class TestMarkRan:
    def test_sets_last_run_at(self, uow):
        row = make_recurring_operation_row(last_run_at=None)
        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)
        ran_at = datetime(2026, 3, 1, tzinfo=timezone.utc)

        entity.mark_ran(ran_at=ran_at)

        assert row.last_run_at == ran_at


class TestBuildTrigger:
    def _next_fire(self, trigger, after: datetime) -> datetime:
        return trigger.get_next_fire_time(after, after)

    def test_daily_fires_every_day_at_the_given_time(self):
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.DAILY, hour=9, minute=30
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        assert isinstance(trigger, CronTrigger)
        start = datetime(2026, 3, 1, tzinfo=timezone.utc)
        first = self._next_fire(trigger, start)
        second = self._next_fire(trigger, first)
        assert first == datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)
        assert second == datetime(2026, 3, 2, 9, 30, tzinfo=timezone.utc)

    def test_weekly_fires_on_the_given_day_of_week(self):
        # 0 = Monday
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.WEEKLY, day_of_week=0, hour=9, minute=0
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        start = datetime(2026, 8, 22, tzinfo=timezone.utc)  # a Saturday
        first = self._next_fire(trigger, start)
        assert first.strftime("%A") == "Monday"

    def test_monthly_fires_on_the_given_day_of_month(self):
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.MONTHLY, day_of_month=3, hour=0, minute=0
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        first = self._next_fire(trigger, datetime(2026, 3, 1, tzinfo=timezone.utc))
        assert first == datetime(2026, 3, 3, tzinfo=timezone.utc)

    def test_monthly_day_of_month_minus_one_means_last_day_of_month(self):
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.MONTHLY, day_of_month=-1, hour=0, minute=0
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        assert isinstance(trigger, MonthEndOffsetTrigger)
        # February 2026 is not a leap year -> 28 days
        first = self._next_fire(trigger, datetime(2026, 2, 1, tzinfo=timezone.utc))
        assert first == datetime(2026, 2, 28, tzinfo=timezone.utc)

    def test_monthly_day_of_month_minus_two_means_second_to_last_day_of_month(self):
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.MONTHLY, day_of_month=-2, hour=0, minute=0
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        # February 2026 -> 28 days, second-to-last is the 27th
        first = self._next_fire(trigger, datetime(2026, 2, 1, tzinfo=timezone.utc))
        assert first == datetime(2026, 2, 27, tzinfo=timezone.utc)
        # April 2026 -> 30 days, second-to-last is the 29th
        second = self._next_fire(trigger, datetime(2026, 4, 1, tzinfo=timezone.utc))
        assert second == datetime(2026, 4, 29, tzinfo=timezone.utc)

    def test_monthly_day_of_month_offset_skips_months_too_short_to_contain_it(self):
        # -31 means "31st from the end" -> only exists in 31-day months (day 1)
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.MONTHLY, day_of_month=-31, hour=0, minute=0
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        # March (31 days) -> next valid one is May (31 days), skipping April (30 days)
        first = self._next_fire(trigger, datetime(2026, 3, 1, tzinfo=timezone.utc))
        assert first == datetime(2026, 5, 1, tzinfo=timezone.utc)

    def test_yearly_fires_on_the_given_month_and_day(self):
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.YEARLY, month=12, day_of_month=25, hour=0, minute=0
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        first = self._next_fire(trigger, datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert first == datetime(2026, 12, 25, tzinfo=timezone.utc)

    def test_yearly_day_of_month_offset_means_nth_from_end_within_the_given_month(self):
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.YEARLY, month=2, day_of_month=-1, hour=0, minute=0
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        # 2026 is not a leap year -> last day of February is the 28th
        first = self._next_fire(trigger, datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert first == datetime(2026, 2, 28, tzinfo=timezone.utc)

        # 2027 is not a leap year either -> the 28th again
        second = self._next_fire(trigger, first)
        assert second == datetime(2027, 2, 28, tzinfo=timezone.utc)

        # 2028 is a leap year -> last day of February is the 29th
        third = self._next_fire(trigger, second)
        assert third == datetime(2028, 2, 29, tzinfo=timezone.utc)


class TestValidateSchedule:
    def test_daily_accepts_no_schedule_fields(self):
        RecurringOperationEntity.validate_schedule(
            interval=RecurrenceIntervalEnum.DAILY, day_of_month=None, day_of_week=None, month=None
        )  # must not raise

    def test_daily_rejects_day_of_month(self):
        with pytest.raises(BadRequestError):
            RecurringOperationEntity.validate_schedule(
                interval=RecurrenceIntervalEnum.DAILY, day_of_month=1, day_of_week=None, month=None
            )

    def test_weekly_requires_day_of_week_in_range(self):
        with pytest.raises(BadRequestError):
            RecurringOperationEntity.validate_schedule(
                interval=RecurrenceIntervalEnum.WEEKLY, day_of_month=None, day_of_week=7, month=None
            )

    @pytest.mark.parametrize("day_of_month", [1, 15, 31, -1, -15, -31])
    def test_monthly_accepts_valid_day_of_month(self, day_of_month):
        RecurringOperationEntity.validate_schedule(
            interval=RecurrenceIntervalEnum.MONTHLY,
            day_of_month=day_of_month,
            day_of_week=None,
            month=None,
        )  # must not raise

    @pytest.mark.parametrize("day_of_month", [None, 0, 32, -32])
    def test_monthly_rejects_invalid_day_of_month(self, day_of_month):
        with pytest.raises(BadRequestError):
            RecurringOperationEntity.validate_schedule(
                interval=RecurrenceIntervalEnum.MONTHLY,
                day_of_month=day_of_month,
                day_of_week=None,
                month=None,
            )

    def test_yearly_accepts_a_leap_year_only_offset(self):
        # -29 in February can only ever occur on leap years -> allowed, just rare
        RecurringOperationEntity.validate_schedule(
            interval=RecurrenceIntervalEnum.YEARLY, day_of_month=-29, day_of_week=None, month=2
        )  # must not raise

    def test_yearly_rejects_an_offset_that_can_never_occur_in_the_given_month(self):
        # February never has 30 days
        with pytest.raises(BadRequestError):
            RecurringOperationEntity.validate_schedule(
                interval=RecurrenceIntervalEnum.YEARLY, day_of_month=-30, day_of_week=None, month=2
            )
