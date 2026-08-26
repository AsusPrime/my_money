from fastapi import APIRouter
from fastapi import status
from loguru import logger

from src.schemas.balance_group import BalanceGroupCreateSchema
from src.schemas.balance_group import BalanceGroupListResponseSchema
from src.schemas.balance_group import BalanceGroupResponseSchema
from src.schemas.balance_group import BalanceGroupUpdateSchema
from src.services.dependencies.balance_group_dep import BalanceGroupServiceDep
from src.utils.dependencies.uow_dep import UOWDep

router = APIRouter(
    prefix="/balance-groups",
    tags=["Balance Groups"],
)


@router.get(
    "",
    response_model=BalanceGroupListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_balance_groups_api(
    account_id: int, uow: UOWDep, balance_group_service: BalanceGroupServiceDep
):
    return await balance_group_service.get_all_balance_groups_by_account_id(
        uow=uow, account_id=account_id
    )


@router.post(
    "",
    response_model=BalanceGroupResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_balance_group_api(
    body: BalanceGroupCreateSchema, uow: UOWDep, balance_group_service: BalanceGroupServiceDep
):
    new_group = await balance_group_service.create_balance_group(uow=uow, group_data=body)
    logger.info(f"Balance group created: {new_group.id}")
    return new_group


@router.patch(
    "/{group_id}",
    response_model=BalanceGroupResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_balance_group_api(
    group_id: int,
    body: BalanceGroupUpdateSchema,
    uow: UOWDep,
    balance_group_service: BalanceGroupServiceDep,
):
    updated_group = await balance_group_service.update_balance_group_by_id(
        uow=uow, group_id=group_id, group_data=body
    )
    logger.info(f"Balance group updated: {group_id}")
    return updated_group


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_balance_group_api(
    group_id: int, uow: UOWDep, balance_group_service: BalanceGroupServiceDep
):
    await balance_group_service.delete_balance_group_by_id(uow=uow, group_id=group_id)
