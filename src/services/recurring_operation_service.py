from datetime import datetime, timezone

from loguru import logger

from src.common.constants import RECURRING_OPERATION_SUPPORTED_TYPES
from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import BadRequestError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.entities.recurring_operation import RecurringOperationEntity
from src.enums.enums import OperationTypeEnum
from src.enums.enums import RecurrenceIntervalEnum
from src.schemas.ledger import RecordSingleLegOperationPayload
from src.schemas.recurring_operation import RecurringOperationCreateSchema
from src.schemas.recurring_operation import RecurringOperationListResponseSchema
from src.schemas.recurring_operation import RecurringOperationResponseSchema
from src.schemas.recurring_operation import RecurringOperationUpdateSchema
from src.services.balance_service import BalanceService
from src.services.currency_service import CurrencyService
from src.services.ledger_service import LedgerService
from src.utils.uow.unitofwork import IUnitOfWork


class RecurringOperationService:

    @staticmethod
    async def get_all_recurring_operations(
        uow: IUnitOfWork, balance_id: int | None = None
    ) -> RecurringOperationListResponseSchema:
        filters = {} if balance_id is None else {"balance_id": balance_id}
        rows = await uow.recurring_operations.find_all(**filters)
        return RecurringOperationListResponseSchema(
            items=[RecurringOperationResponseSchema.model_validate(r) for r in rows]
        )

    @staticmethod
    async def get_recurring_operation_by_id(
        uow: IUnitOfWork, recurring_operation_id: int
    ) -> RecurringOperationResponseSchema:
        row = await uow.recurring_operations.find_one_or_none(id=recurring_operation_id)

        if row is None:
            raise NotFoundError(Messages.RECURRING_OPERATION_NOT_FOUND)

        return RecurringOperationResponseSchema.model_validate(row)

    @staticmethod
    async def create_recurring_operation(
        uow: IUnitOfWork,
        data: RecurringOperationCreateSchema,
        balance_service: BalanceService = BalanceService(),
        currency_service: CurrencyService = CurrencyService(),
    ) -> RecurringOperationResponseSchema:
        if data.operation_type not in RECURRING_OPERATION_SUPPORTED_TYPES:
            raise BadRequestError(Messages.RECURRING_OPERATION_TYPE_NOT_SUPPORTED)

        RecurringOperationService._validate_schedule(
            interval=data.interval,
            day_of_month=data.day_of_month,
            day_of_week=data.day_of_week,
            month=data.month,
        )

        await balance_service.get_active_balance_by_id(uow=uow, balance_id=data.balance_id)
        await currency_service.get_currency_by_ticker(uow=uow, ticker=data.currency_ticker)

        new_row = await uow.recurring_operations.add_one(data=data.model_dump())

        if new_row is None:
            logger.error(Messages.ERROR_FILLED_TO_ADD_NEW_RECURRING_OPERATION)
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_RECURRING_OPERATION)

        return RecurringOperationResponseSchema.model_validate(new_row)

    @staticmethod
    async def update_recurring_operation_by_id(
        uow: IUnitOfWork, recurring_operation_id: int, data: RecurringOperationUpdateSchema
    ) -> RecurringOperationResponseSchema:
        updated_row = await uow.recurring_operations.edit_one(
            id=recurring_operation_id, data=data.model_dump(exclude_unset=True)
        )

        if updated_row is None:
            raise NotFoundError(Messages.RECURRING_OPERATION_NOT_FOUND)

        schedule_fields_touched = any(
            field is not None
            for field in (data.interval, data.day_of_month, data.day_of_week, data.month)
        )
        if schedule_fields_touched:
            RecurringOperationService._validate_schedule(
                interval=updated_row.interval,
                day_of_month=updated_row.day_of_month,
                day_of_week=updated_row.day_of_week,
                month=updated_row.month,
            )

        return RecurringOperationResponseSchema.model_validate(updated_row)

    @staticmethod
    async def delete_recurring_operation_by_id(
        uow: IUnitOfWork, recurring_operation_id: int
    ) -> None:
        deleted_row = await uow.recurring_operations.delete_one(_id=recurring_operation_id)

        if deleted_row is None:
            raise NotFoundError(Messages.RECURRING_OPERATION_NOT_FOUND)

    @staticmethod
    async def run(
        uow: IUnitOfWork, recurring_operation_id: int, occurred_at: datetime | None = None
    ) -> None:
        row = await uow.recurring_operations.find_one_or_none(id=recurring_operation_id)
        if row is None or not row.is_active:
            return

        entity = RecurringOperationEntity(recurring_operation=row, uow=uow)
        ran_at = occurred_at or datetime.now(timezone.utc)

        try:
            amount = await entity.resolve_amount()
            payload = RecordSingleLegOperationPayload(
                operation_type=OperationTypeEnum(row.operation_type),
                balance_id=row.balance_id,
                amount=amount,
                currency_ticker=row.currency_ticker,
                category_id=row.category_id,
                counterparty=row.counterparty,
                note=row.note,
                executed_at=ran_at,
            )
            await LedgerService.record_operation(uow=uow, payload=payload)
        except Exception as e:
            logger.warning(f"Recurring operation {recurring_operation_id} failed to run: {e}")

        entity.mark_ran(ran_at=ran_at)


    @staticmethod
    def _validate_schedule(
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
            if day_of_month is None or not (day_of_month == -1 or 1 <= day_of_month <= 31):
                logger.warning("MONTHLY recurring operation requires day_of_month in 1..31 or -1")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
            if day_of_week is not None or month is not None:
                logger.warning("MONTHLY recurring operation must not set day_of_week/month")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)

        elif interval == RecurrenceIntervalEnum.YEARLY:
            if month is None or not (1 <= month <= 12):
                logger.warning("YEARLY recurring operation requires month in 1..12")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
            if day_of_month is None or not (day_of_month == -1 or 1 <= day_of_month <= 31):
                logger.warning("YEARLY recurring operation requires day_of_month in 1..31 or -1")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
            if day_of_week is not None:
                logger.warning("YEARLY recurring operation must not set day_of_week")
                raise BadRequestError(Messages.RECURRING_OPERATION_INVALID_SCHEDULE)
