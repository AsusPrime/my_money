from datetime import datetime
from decimal import Decimal

from apscheduler.triggers.cron import CronTrigger

from src.enums.enums import AmountModeEnum
from src.enums.enums import RecurrenceIntervalEnum
from src.models import RecurringOperation
from src.utils.uow.unitofwork import IUnitOfWork


class RecurringOperationEntity:
    def __init__(self, recurring_operation: RecurringOperation, uow: IUnitOfWork) -> None:
        self._recurring_operation = recurring_operation
        self._uow = uow

    async def resolve_amount(self) -> Decimal:
        if self._recurring_operation.amount_mode == AmountModeEnum.FIXED:
            return self._recurring_operation.amount_value

        amounts = await self._uow.ledgers.get_amounts_by_balance_id(
            balance_id=self._recurring_operation.balance_id
        )
        current = amounts.get(self._recurring_operation.currency_ticker, Decimal("0"))
        return current * (self._recurring_operation.amount_value / Decimal("100"))

    def mark_ran(self, ran_at: datetime) -> None:
        self._recurring_operation.last_run_at = ran_at

    @staticmethod
    def build_trigger(recurring_operation: RecurringOperation) -> CronTrigger:
        interval = recurring_operation.interval
        hour = recurring_operation.hour
        minute = recurring_operation.minute

        if interval == RecurrenceIntervalEnum.DAILY:
            return CronTrigger(hour=hour, minute=minute, timezone="UTC")

        if interval == RecurrenceIntervalEnum.WEEKLY:
            return CronTrigger(
                day_of_week=recurring_operation.day_of_week,
                hour=hour,
                minute=minute,
                timezone="UTC",
            )

        if interval == RecurrenceIntervalEnum.MONTHLY:
            day = RecurringOperationEntity._day_expression(recurring_operation.day_of_month)
            return CronTrigger(day=day, hour=hour, minute=minute, timezone="UTC")

        if interval == RecurrenceIntervalEnum.YEARLY:
            day = RecurringOperationEntity._day_expression(recurring_operation.day_of_month)
            return CronTrigger(
                month=recurring_operation.month, day=day, hour=hour, minute=minute, timezone="UTC"
            )

        raise ValueError(f"Unsupported interval: {interval}")

    @staticmethod
    def _day_expression(day_of_month: int) -> str | int:
        return "last" if day_of_month == -1 else day_of_month
