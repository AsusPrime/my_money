from fastapi import APIRouter
from fastapi import status
from loguru import logger

from src.schemas.ledger import LedgerListResponseSchema, RecordSingleLegOperationPayload, RecordTradePayload, RecordTransferPayload
from src.schemas.ledger import LedgerResponseSchema
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
