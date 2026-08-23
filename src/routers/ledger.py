from fastapi import APIRouter
from fastapi import status
from loguru import logger

from src.schemas.ledger import LedgerListResponseSchema, RecordSingleLegOperationPayload, RecordTradePayload, RecordTransferPayload
from src.schemas.ledger import LedgerResponseSchema
from src.schemas.ledger import LedgerUpdateSchema
from src.services.dependencies.ledger_dep import LedgerServiceDep
from src.utils.dependencies.uow_dep import UOWDep

router = APIRouter(
    prefix="/ledger",
    tags=["Ledger"],
)


@router.post(
    "/operations",
    response_model=LedgerResponseSchema | LedgerListResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def record_operation_api(
    body: RecordSingleLegOperationPayload | RecordTransferPayload | RecordTradePayload, uow: UOWDep, ledger_service: LedgerServiceDep
):
    result = await ledger_service.record_operation(uow=uow, payload=body)
    logger.info(f"Ledger operation recorded: {body.operation_type}")
    return result


@router.get(
    "/operations/{ledger_id}/group",
    response_model=LedgerResponseSchema | LedgerListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_operation_group_api(
    ledger_id: int, uow: UOWDep, ledger_service: LedgerServiceDep
):
    return await ledger_service.get_operation_group_by_ledger_id(uow=uow, ledger_id=ledger_id)


@router.patch(
    "/operations/{ledger_id}",
    response_model=LedgerResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_ledger_entry_api(
    ledger_id: int, body: LedgerUpdateSchema, uow: UOWDep, ledger_service: LedgerServiceDep
):
    result = await ledger_service.update_ledger_by_id(uow=uow, ledger_id=ledger_id, ledger_data=body)
    logger.info(f"Ledger entry updated: {ledger_id}")
    return result


@router.put(
    "/operations/{ledger_id}",
    response_model=LedgerResponseSchema | LedgerListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def replace_operation_api(
    ledger_id: int,
    body: RecordSingleLegOperationPayload | RecordTransferPayload | RecordTradePayload,
    uow: UOWDep,
    ledger_service: LedgerServiceDep,
):
    result = await ledger_service.replace_operation(uow=uow, ledger_id=ledger_id, payload=body)
    logger.info(f"Ledger operation replaced: {ledger_id}")
    return result


@router.delete(
    "/operations/{ledger_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_operation_api(
    ledger_id: int, uow: UOWDep, ledger_service: LedgerServiceDep
):
    await ledger_service.delete_operation_by_id(uow=uow, ledger_id=ledger_id)
    logger.info(f"Ledger operation deleted: {ledger_id}")
