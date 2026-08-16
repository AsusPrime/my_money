from fastapi import APIRouter
from fastapi import status
from loguru import logger

from src.schemas.balance import BalanceCreateSchema
from src.schemas.balance import BalanceListResponseSchema
from src.schemas.balance import BalanceResponseSchema
from src.schemas.balance import BalanceUpdateSchema
from src.schemas.ledger import LedgerListResponseSchema
from src.services.dependencies.balance_dep import BalanceServiceDep
from src.services.dependencies.ledger_dep import LedgerServiceDep
from src.utils.dependencies.uow_dep import UOWDep

router = APIRouter(
    prefix="/balances",
    tags=["Balances"],
)


@router.get(
    "",
    response_model=BalanceListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_balances_api(
    account_id: int, uow: UOWDep, balance_service: BalanceServiceDep
):
    return await balance_service.get_all_balances_by_account_id(
        uow=uow, account_id=account_id
    )


@router.get(
    "/{balance_id}",
    response_model=BalanceResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_balance_api(
    balance_id: int, uow: UOWDep, balance_service: BalanceServiceDep
):
    return await balance_service.get_balance_by_id(uow=uow, balance_id=balance_id)


@router.get(
    "/{balance_id}/ledgers",
    response_model=LedgerListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_balance_ledger_api(
    balance_id: int, uow: UOWDep, ledger_service: LedgerServiceDep
):
    return await ledger_service.get_operations_by_balance_id(
        uow=uow, balance_id=balance_id
    )


@router.post(
    "",
    response_model=BalanceResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_balance_api(
    body: BalanceCreateSchema, uow: UOWDep, balance_service: BalanceServiceDep
):
    new_balance = await balance_service.create_balance(uow=uow, balance_data=body)
    logger.info(f"Balance created: {new_balance.id}")
    return new_balance


@router.patch(
    "/{balance_id}",
    response_model=BalanceResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_balance_api(
    balance_id: int,
    body: BalanceUpdateSchema,
    uow: UOWDep,
    balance_service: BalanceServiceDep,
):
    updated_balance = await balance_service.update_balance(
        uow=uow, balance_id=balance_id, balance_data=body
    )
    logger.info(f"Balance updated: {balance_id}")
    return updated_balance


@router.post(
    "/{balance_id}/archive",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def archive_balance_api(
    balance_id: int, uow: UOWDep, balance_service: BalanceServiceDep
):
    await balance_service.archive_balance(uow=uow, balance_id=balance_id)
