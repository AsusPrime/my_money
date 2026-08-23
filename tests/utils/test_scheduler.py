from datetime import datetime
from datetime import timezone
from unittest.mock import AsyncMock
from unittest.mock import patch

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger

from src.enums.enums import RecurrenceIntervalEnum
from src.utils.scheduler.scheduler import RecurringOperationScheduler
from tests.services.conftest import FakeUnitOfWork
from tests.services.conftest import make_recurring_operation_row


class TestSchedule:
    async def test_adds_a_job_with_the_row_s_trigger(self):
        recurring_operation_scheduler = RecurringOperationScheduler()
        uow = FakeUnitOfWork()
        uow.recurring_operations.find_one_or_none.return_value = make_recurring_operation_row(
            id=1
        )

        with (
            patch("src.utils.scheduler.scheduler.UnitOfWork", return_value=uow),
            patch.object(recurring_operation_scheduler.scheduler, "add_job") as mocked,
        ):
            await recurring_operation_scheduler.schedule(1)

        _, kwargs = mocked.call_args
        assert isinstance(kwargs["trigger"], CronTrigger)
        assert kwargs["args"] == [1]
        assert kwargs["id"] == "recurring_operation_1"
        assert kwargs["replace_existing"] is True
        # a live job must never be silently dropped for firing a moment late
        # under real request load (APScheduler's default grace window is 1s)
        assert kwargs["misfire_grace_time"] is None

    async def test_does_nothing_when_the_row_is_missing(self):
        recurring_operation_scheduler = RecurringOperationScheduler()
        uow = FakeUnitOfWork()
        uow.recurring_operations.find_one_or_none.return_value = None

        with (
            patch("src.utils.scheduler.scheduler.UnitOfWork", return_value=uow),
            patch.object(recurring_operation_scheduler.scheduler, "add_job") as mocked,
        ):
            await recurring_operation_scheduler.schedule(999)

        mocked.assert_not_called()


class TestUnschedule:
    def test_removes_the_job(self):
        recurring_operation_scheduler = RecurringOperationScheduler()
        with patch.object(recurring_operation_scheduler.scheduler, "remove_job") as mocked:
            recurring_operation_scheduler.unschedule(1)

        mocked.assert_called_once_with("recurring_operation_1")

    def test_does_not_raise_when_job_is_missing(self):
        recurring_operation_scheduler = RecurringOperationScheduler()
        with patch.object(
            recurring_operation_scheduler.scheduler,
            "remove_job",
            side_effect=JobLookupError("recurring_operation_1"),
        ):
            recurring_operation_scheduler.unschedule(1)  # must not raise


class TestStop:
    def test_shuts_down_the_scheduler(self):
        recurring_operation_scheduler = RecurringOperationScheduler()
        with patch.object(recurring_operation_scheduler.scheduler, "shutdown") as mocked:
            recurring_operation_scheduler.stop()

        mocked.assert_called_once_with(wait=False)


class TestStart:
    async def test_catches_up_and_schedules_every_active_row(self):
        recurring_operation_scheduler = RecurringOperationScheduler()
        uow = FakeUnitOfWork()
        rows = [make_recurring_operation_row(id=1), make_recurring_operation_row(id=2)]
        uow.recurring_operations.find_all_active.return_value = rows

        with (
            patch.object(recurring_operation_scheduler.scheduler, "start"),
            patch("src.utils.scheduler.scheduler.UnitOfWork", return_value=uow),
            patch.object(
                RecurringOperationScheduler, "_catch_up", new=AsyncMock()
            ) as mocked_catch_up,
            patch.object(
                recurring_operation_scheduler, "schedule", new=AsyncMock()
            ) as mocked_schedule,
        ):
            await recurring_operation_scheduler.start()

        assert mocked_catch_up.await_count == 2
        assert mocked_schedule.await_count == 2
        mocked_schedule.assert_any_await(1)
        mocked_schedule.assert_any_await(2)


class TestRun:
    async def test_runs_through_the_service(self):
        uow = FakeUnitOfWork()
        with (
            patch("src.utils.scheduler.scheduler.UnitOfWork", return_value=uow),
            patch(
                "src.utils.scheduler.scheduler.RecurringOperationService.run", new=AsyncMock()
            ) as mocked_run,
        ):
            await RecurringOperationScheduler._run(1)

        mocked_run.assert_awaited_once_with(uow=uow, recurring_operation_id=1)

    async def test_does_not_raise_when_the_service_fails(self):
        uow = FakeUnitOfWork()
        with (
            patch("src.utils.scheduler.scheduler.UnitOfWork", return_value=uow),
            patch(
                "src.utils.scheduler.scheduler.RecurringOperationService.run",
                new=AsyncMock(side_effect=Exception("boom")),
            ),
        ):
            await RecurringOperationScheduler._run(1)  # must not raise


class TestCatchUp:
    async def test_runs_once_per_missed_occurrence(self):
        # DAILY at midnight, last ran 3 days before "now" -> 3 missed occurrences
        row = make_recurring_operation_row(
            id=1,
            interval=RecurrenceIntervalEnum.DAILY,
            day_of_month=None,
            last_run_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        uow = FakeUnitOfWork()

        with (
            patch("src.utils.scheduler.scheduler.UnitOfWork", return_value=uow),
            patch(
                "src.utils.scheduler.scheduler.RecurringOperationService.run", new=AsyncMock()
            ) as mocked_run,
            patch(
                "src.utils.scheduler.scheduler.datetime"
            ) as mocked_datetime,
        ):
            mocked_datetime.now.return_value = datetime(2026, 3, 4, tzinfo=timezone.utc)
            await RecurringOperationScheduler._catch_up(row)

        assert mocked_run.await_count == 3
        occurred_ats = [call.kwargs["occurred_at"] for call in mocked_run.await_args_list]
        assert occurred_ats == [
            datetime(2026, 3, 2, tzinfo=timezone.utc),
            datetime(2026, 3, 3, tzinfo=timezone.utc),
            datetime(2026, 3, 4, tzinfo=timezone.utc),
        ]

    async def test_does_nothing_when_nothing_was_missed(self):
        row = make_recurring_operation_row(
            id=1,
            interval=RecurrenceIntervalEnum.DAILY,
            day_of_month=None,
            last_run_at=datetime.now(timezone.utc),
        )

        with patch(
            "src.utils.scheduler.scheduler.RecurringOperationService.run", new=AsyncMock()
        ) as mocked_run:
            await RecurringOperationScheduler._catch_up(row)

        mocked_run.assert_not_awaited()

    async def test_continues_past_a_failure_in_one_occurrence(self):
        row = make_recurring_operation_row(
            id=1,
            interval=RecurrenceIntervalEnum.DAILY,
            day_of_month=None,
            last_run_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        uow = FakeUnitOfWork()

        with (
            patch("src.utils.scheduler.scheduler.UnitOfWork", return_value=uow),
            patch(
                "src.utils.scheduler.scheduler.RecurringOperationService.run",
                new=AsyncMock(side_effect=[Exception("boom"), None, None]),
            ) as mocked_run,
            patch("src.utils.scheduler.scheduler.datetime") as mocked_datetime,
        ):
            mocked_datetime.now.return_value = datetime(2026, 3, 4, tzinfo=timezone.utc)
            await RecurringOperationScheduler._catch_up(row)  # must not raise

        assert mocked_run.await_count == 3
