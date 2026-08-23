from datetime import datetime, timezone

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from src.entities.recurring_operation import RecurringOperationEntity
from src.models import RecurringOperation
from src.services.recurring_operation_service import RecurringOperationService
from src.utils.uow.unitofwork import UnitOfWork


class RecurringOperationScheduler:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    async def start(self) -> None:
        self.scheduler.start()

        async with UnitOfWork() as uow:
            rows = await uow.recurring_operations.find_all_active()

        for row in rows:
            await self._catch_up(row)
            await self.schedule(row.id)

        logger.info(f"[RecurringOperationScheduler] Started with {len(rows)} active job(s)")

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("[RecurringOperationScheduler] Stopped")

    async def schedule(self, recurring_operation_id: int) -> None:
        async with UnitOfWork() as uow:
            row = await uow.recurring_operations.find_one_or_none(id=recurring_operation_id)

        if row is None:
            return

        trigger = RecurringOperationEntity.build_trigger(row)
        self.scheduler.add_job(
            self._run,
            trigger=trigger,
            args=[row.id],
            id=self._job_id(row.id),
            replace_existing=True,
            misfire_grace_time=None,
        )

    def unschedule(self, recurring_operation_id: int) -> None:
        try:
            self.scheduler.remove_job(self._job_id(recurring_operation_id))
        except JobLookupError:
            pass

    @staticmethod
    def _job_id(recurring_operation_id: int) -> str:
        return f"recurring_operation_{recurring_operation_id}"

    @staticmethod
    async def _run(recurring_operation_id: int) -> None:
        try:
            async with UnitOfWork() as uow:
                await RecurringOperationService.run(
                    uow=uow, recurring_operation_id=recurring_operation_id
                )
        except Exception as e:
            logger.error(
                f"[RecurringOperationScheduler] Failed to run "
                f"recurring operation {recurring_operation_id}: {e}"
            )

    @staticmethod
    async def _catch_up(recurring_operation: RecurringOperation) -> None:
        trigger = RecurringOperationEntity.build_trigger(recurring_operation)
        now = datetime.now(timezone.utc)
        cursor = recurring_operation.last_run_at or recurring_operation.created_at

        missed_at = []
        while True:
            next_fire = trigger.get_next_fire_time(cursor, now)
            if next_fire is None or next_fire > now:
                break
            missed_at.append(next_fire)
            cursor = next_fire

        for occurred_at in missed_at:
            try:
                async with UnitOfWork() as uow:
                    await RecurringOperationService.run(
                        uow=uow,
                        recurring_operation_id=recurring_operation.id,
                        occurred_at=occurred_at,
                    )
            except Exception as e:
                logger.error(
                    f"[RecurringOperationScheduler] Catch-up failed for "
                    f"recurring operation {recurring_operation.id} at {occurred_at}: {e}"
                )

        if missed_at:
            logger.info(
                f"[RecurringOperationScheduler] Caught up {len(missed_at)} missed "
                f"run(s) for recurring operation {recurring_operation.id}"
            )
