from datetime import datetime
from decimal import Decimal

from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from src.common.constants import MAX_DAYS_IN_MONTH
from src.core.exceptions.exceptions import BadRequestError
from src.core.messages.messages import Messages
from src.enums.enums import AmountModeEnum
from src.enums.enums import RecurrenceIntervalEnum
from src.models import RecurringOperation
from src.utils.triggers.triggers import MonthEndOffsetTrigger
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
    def build_trigger(recurring_operation: RecurringOperation) -> BaseTrigger:
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
            return RecurringOperationEntity._day_of_month_trigger(
                day_of_month=recurring_operation.day_of_month, hour=hour, minute=minute
            )

        if interval == RecurrenceIntervalEnum.YEARLY:
            return RecurringOperationEntity._day_of_month_trigger(
                day_of_month=recurring_operation.day_of_month,
                hour=hour,
                minute=minute,
                month=recurring_operation.month,
            )

        raise ValueError(f"Unsupported interval: {interval}")

    @staticmethod
    def _day_of_month_trigger(
        day_of_month: int, hour: int, minute: int, month: int | None = None
    ) -> BaseTrigger:
        if day_of_month < 0:
            return MonthEndOffsetTrigger(offset=-day_of_month, hour=hour, minute=minute, month=month)
        return CronTrigger(month=month, day=day_of_month, hour=hour, minute=minute, timezone="UTC")

    @staticmethod
    def validate_schedule(
        interval: RecurrenceIntervalEnum,
        day_of_month: int | None,
        day_of_week: int | None,
        month: int | None,
    ) -> None:
        if interval == RecurrenceIntervalEnum.DAILY:
            if day_of_month is not None or day_of_week is not None or month is not None:
                logger.warning("DAILY recurring operation must not set day_of_month/day_of_week/month")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)

        elif interval == RecurrenceIntervalEnum.WEEKLY:
            if day_of_week is None or not (0 <= day_of_week <= 6):
                logger.warning("WEEKLY recurring operation requires day_of_week in 0..6")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
            if day_of_month is not None or month is not None:
                logger.warning("WEEKLY recurring operation must not set day_of_month/month")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)

        elif interval == RecurrenceIntervalEnum.MONTHLY:
            if day_of_month is None or not RecurringOperationEntity._is_valid_day_of_month(
                day_of_month
            ):
                logger.warning(
                    "MONTHLY recurring operation requires day_of_month in 1..31 (from start) "
                    "or -1..-31 (from end)"
                )
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
            if day_of_week is not None or month is not None:
                logger.warning("MONTHLY recurring operation must not set day_of_week/month")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)

        elif interval == RecurrenceIntervalEnum.YEARLY:
            if month is None or not (1 <= month <= 12):
                logger.warning("YEARLY recurring operation requires month in 1..12")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
            if day_of_month is None or not RecurringOperationEntity._is_valid_day_of_month(
                day_of_month
            ):
                logger.warning(
                    "YEARLY recurring operation requires day_of_month in 1..31 (from start) "
                    "or -1..-31 (from end)"
                )
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
            if not RecurringOperationEntity._can_day_of_month_occur_in_month(day_of_month, month):
                logger.warning(
                    "YEARLY recurring operation's day_of_month can never occur in the given month"
                )
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
            if day_of_week is not None:
                logger.warning("YEARLY recurring operation must not set day_of_week")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)

    @staticmethod
    def _is_valid_day_of_month(day_of_month: int) -> bool:
        """1..31 counted from the start of the month, or -1..-31 counted from the end."""
        return day_of_month != 0 and -31 <= day_of_month <= 31

    @staticmethod
    def _can_day_of_month_occur_in_month(day_of_month: int, month: int) -> bool:
        """Whether a YEARLY schedule's day_of_month can ever occur in the given month.

        Positive days are always fine — APScheduler's CronTrigger just skips years
        where the month is too short. A negative (from-the-end) offset needs an
        explicit check since MonthEndOffsetTrigger would otherwise skip *every* year.
        """
        if day_of_month >= 0:
            return True
        return -day_of_month <= MAX_DAYS_IN_MONTH[month]
