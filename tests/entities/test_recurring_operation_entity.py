from datetime import datetime
from datetime import timezone
from decimal import Decimal

from apscheduler.triggers.cron import CronTrigger

from src.enums.enums import AmountModeEnum
from src.enums.enums import RecurrenceIntervalEnum
from src.entities.recurring_operation import RecurringOperationEntity
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
        row = make_recurring_operation_row(
            balance_id=1,
            currency_ticker="USD",
            amount_mode=AmountModeEnum.PERCENT_OF_BALANCE,
            amount_value=Decimal("2.5"),
        )
        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)

        result = await entity.resolve_amount()

        assert result == Decimal("25.0")
        uow.ledgers.get_amounts_by_balance_id.assert_awaited_once_with(balance_id=1)

    async def test_percent_of_balance_is_zero_when_currency_has_no_funds(self, uow):
        uow.ledgers.get_amounts_by_balance_id.return_value = {}
        row = make_recurring_operation_row(
            currency_ticker="USD",
            amount_mode=AmountModeEnum.PERCENT_OF_BALANCE,
            amount_value=Decimal("2.5"),
        )
        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)

        result = await entity.resolve_amount()

        assert result == Decimal("0")


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

        # February 2026 is not a leap year -> 28 days
        first = self._next_fire(trigger, datetime(2026, 2, 1, tzinfo=timezone.utc))
        assert first == datetime(2026, 2, 28, tzinfo=timezone.utc)

    def test_yearly_fires_on_the_given_month_and_day(self):
        row = make_recurring_operation_row(
            interval=RecurrenceIntervalEnum.YEARLY, month=12, day_of_month=25, hour=0, minute=0
        )

        trigger = RecurringOperationEntity.build_trigger(row)

        first = self._next_fire(trigger, datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert first == datetime(2026, 12, 25, tzinfo=timezone.utc)
