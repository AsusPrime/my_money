from uuid import UUID

from fastapi import APIRouter
from fastapi import status
from loguru import logger

from src.services.dependencies.account_dep import AccountServiceDep
from src.utils.dependencies.uow_dep import UOWDep
from src.schemas.account import AccountCreateSchema
from src.schemas.account import AccountListResponseSchema
from src.schemas.account import AccountResponseSchema
from src.schemas.account import AccountUpdateSchema

router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)


@router.get(
    "",
    response_model=AccountListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_accounts_api(uow: UOWDep, account_service: AccountServiceDep):
    return await account_service.get_all_accounts(uow=uow)


@router.get(
    "/{accountId}",
    response_model=AccountResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_account_api(
    accountId: UUID, uow: UOWDep, account_service: AccountServiceDep
):
    return await account_service.get_account_by_id(uow=uow, accountId=accountId)


@router.post(
    "",
    response_model=AccountResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_account_api(
    body: AccountCreateSchema, uow: UOWDep, account_service: AccountServiceDep
):
    new_account = await account_service.create_account(uow=uow, account_data=body)
    logger.info(f"Account created: {new_account.id}")
    return new_account


@router.patch(
    "/{accountId}",
    response_model=AccountResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_account_api(
    accountId: UUID,
    body: AccountUpdateSchema,
    uow: UOWDep,
    account_service: AccountServiceDep,
):
    updated_account = await account_service.update_account_by_id(
        uow=uow, accountId=accountId, account_data=body
    )
    logger.info(f"Account updated: {accountId}")
    return updated_account


@router.delete(
    "/{accountId}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_account_api(
    accountId: UUID, uow: UOWDep, account_service: AccountServiceDep
):
    await account_service.delete_account_by_id(uow=uow, accountId=accountId)
