from calendar import monthrange
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

from apscheduler.triggers.base import BaseTrigger

from src.common.constants import MONTH_END_OFFSET_TRIGGER_LOOKAHEAD_MONTHS


class MonthEndOffsetTrigger(BaseTrigger):
    """Fires on the Nth-from-last day of the month.

    offset=1 -> last day of month, offset=2 -> second-to-last day, etc.
    A month too short to contain that offset is skipped rather than clamped —
    the same semantics iCalendar's RRULE BYMONTHDAY uses for negative values.
    """

    def __init__(
        self,
        offset: int,
        hour: int,
        minute: int,
        month: int | None = None,
        timezone_name: str = "UTC",
    ) -> None:
        self._offset = offset
        self._hour = hour
        self._minute = minute
        self._month = month
        self._timezone = ZoneInfo(timezone_name)

    def get_next_fire_time(
        self, previous_fire_time: datetime | None, now: datetime
    ) -> datetime | None:
        start_after = previous_fire_time or (now - timedelta(microseconds=1))
        year, month = start_after.year, start_after.month

        for _ in range(MONTH_END_OFFSET_TRIGGER_LOOKAHEAD_MONTHS):
            if self._month is None or month == self._month:
                day = self._day_for(year, month)
                if day is not None:
                    candidate = datetime(
                        year, month, day, self._hour, self._minute, tzinfo=self._timezone
                    )
                    if candidate > start_after:
                        return candidate
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)

        return None

    def _day_for(self, year: int, month: int) -> int | None:
        days_in_month = monthrange(year, month)[1]
        day = days_in_month - self._offset + 1
        return day if day >= 1 else None
