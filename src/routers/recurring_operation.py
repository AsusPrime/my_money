from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Request
from fastapi import status
from loguru import logger

from src.schemas.recurring_operation import RecurringOperationCreateSchema
from src.schemas.recurring_operation import RecurringOperationListResponseSchema
from src.schemas.recurring_operation import RecurringOperationResponseSchema
from src.schemas.recurring_operation import RecurringOperationUpdateSchema
from src.services.dependencies.recurring_operation_dep import RecurringOperationServiceDep
from src.utils.dependencies.uow_dep import UOWDep

router = APIRouter(
    prefix="/recurring-operations",
    tags=["Recurring Operations"],
)


@router.get(
    "",
    response_model=RecurringOperationListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_recurring_operations_api(
    uow: UOWDep,
    recurring_operation_service: RecurringOperationServiceDep,
    balance_id: int | None = None,
):
    return await recurring_operation_service.get_all_recurring_operations(
        uow=uow, balance_id=balance_id
    )


@router.get(
    "/{recurring_operation_id}",
    response_model=RecurringOperationResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_recurring_operation_api(
    recurring_operation_id: int,
    uow: UOWDep,
    recurring_operation_service: RecurringOperationServiceDep,
):
    return await recurring_operation_service.get_recurring_operation_by_id(
        uow=uow, recurring_operation_id=recurring_operation_id
    )


@router.post(
    "",
    response_model=RecurringOperationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_recurring_operation_api(
    body: RecurringOperationCreateSchema,
    uow: UOWDep,
    recurring_operation_service: RecurringOperationServiceDep,
    request: Request,
    background_tasks: BackgroundTasks,
):
    new_row = await recurring_operation_service.create_recurring_operation(uow=uow, data=body)
    background_tasks.add_task(request.app.state.recurring_operation_scheduler.schedule, new_row.id)
    logger.info(f"Recurring operation created: {new_row.id}")
    return new_row


@router.patch(
    "/{recurring_operation_id}",
    response_model=RecurringOperationResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_recurring_operation_api(
    recurring_operation_id: int,
    body: RecurringOperationUpdateSchema,
    uow: UOWDep,
    recurring_operation_service: RecurringOperationServiceDep,
    request: Request,
    background_tasks: BackgroundTasks,
):
    updated_row = await recurring_operation_service.update_recurring_operation_by_id(
        uow=uow, recurring_operation_id=recurring_operation_id, data=body
    )
    if body.is_active is not None:
        scheduler = request.app.state.recurring_operation_scheduler
        if updated_row.is_active:
            background_tasks.add_task(scheduler.schedule, updated_row.id)
        else:
            background_tasks.add_task(scheduler.unschedule, updated_row.id)
    logger.info(f"Recurring operation updated: {recurring_operation_id}")
    return updated_row


@router.delete(
    "/{recurring_operation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recurring_operation_api(
    recurring_operation_id: int,
    uow: UOWDep,
    recurring_operation_service: RecurringOperationServiceDep,
    request: Request,
):
    await recurring_operation_service.delete_recurring_operation_by_id(
        uow=uow, recurring_operation_id=recurring_operation_id
    )
    request.app.state.recurring_operation_scheduler.unschedule(recurring_operation_id)
