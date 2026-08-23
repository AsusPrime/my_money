from datetime import datetime
from datetime import timezone

from src.utils.triggers.triggers import MonthEndOffsetTrigger


class TestMonthEndOffsetTrigger:
    def test_offset_one_is_the_last_day_of_month(self):
        trigger = MonthEndOffsetTrigger(offset=1, hour=0, minute=0)

        first = trigger.get_next_fire_time(
            None, datetime(2026, 2, 1, tzinfo=timezone.utc)
        )

        assert first == datetime(2026, 2, 28, tzinfo=timezone.utc)

    def test_offset_two_is_the_second_to_last_day(self):
        trigger = MonthEndOffsetTrigger(offset=2, hour=0, minute=0)

        first = trigger.get_next_fire_time(
            None, datetime(2026, 4, 1, tzinfo=timezone.utc)
        )

        assert first == datetime(2026, 4, 29, tzinfo=timezone.utc)

    def test_walks_forward_from_the_previous_fire_time(self):
        trigger = MonthEndOffsetTrigger(offset=1, hour=0, minute=0)
        first = datetime(2026, 1, 31, tzinfo=timezone.utc)

        second = trigger.get_next_fire_time(first, first)

        assert second == datetime(2026, 2, 28, tzinfo=timezone.utc)

    def test_skips_months_too_short_to_contain_the_offset(self):
        # offset=31 ("31st from the end") only exists in 31-day months, as day 1
        trigger = MonthEndOffsetTrigger(offset=31, hour=0, minute=0)

        first = trigger.get_next_fire_time(
            datetime(2026, 3, 1, tzinfo=timezone.utc), datetime(2026, 3, 1, tzinfo=timezone.utc)
        )

        # April has 30 days -> skipped, May has 31 -> day 1
        assert first == datetime(2026, 5, 1, tzinfo=timezone.utc)

    def test_respects_hour_and_minute(self):
        trigger = MonthEndOffsetTrigger(offset=1, hour=14, minute=45)

        first = trigger.get_next_fire_time(
            None, datetime(2026, 2, 1, tzinfo=timezone.utc)
        )

        assert first == datetime(2026, 2, 28, 14, 45, tzinfo=timezone.utc)

    def test_restricts_to_a_specific_month_when_given(self):
        trigger = MonthEndOffsetTrigger(offset=1, hour=0, minute=0, month=2)

        first = trigger.get_next_fire_time(
            None, datetime(2026, 1, 1, tzinfo=timezone.utc)
        )

        assert first == datetime(2026, 2, 28, tzinfo=timezone.utc)

    def test_returns_none_when_the_offset_can_never_occur_in_the_fixed_month(self):
        # February never has 30 days -> this configuration is permanently invalid
        trigger = MonthEndOffsetTrigger(offset=30, hour=0, minute=0, month=2)

        result = trigger.get_next_fire_time(
            None, datetime(2026, 1, 1, tzinfo=timezone.utc)
        )

        assert result is None
