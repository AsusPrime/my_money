from src.core.exceptions.exceptions import AddRecordError, NotFoundError
from src.core.messages.messages import Messages
from src.schemas.balance_group import BalanceGroupCreateSchema
from src.schemas.balance_group import BalanceGroupListResponseSchema
from src.schemas.balance_group import BalanceGroupResponseSchema
from src.schemas.balance_group import BalanceGroupUpdateSchema
from src.utils.uow.unitofwork import IUnitOfWork


class BalanceGroupService:

    @staticmethod
    async def get_all_balance_groups_by_account_id(
        uow: IUnitOfWork, account_id: int
    ) -> BalanceGroupListResponseSchema:
        groups = await uow.balance_groups.find_all(account_id=account_id)

        return BalanceGroupListResponseSchema(
            items=[BalanceGroupResponseSchema.model_validate(g) for g in groups]
        )

    @staticmethod
    async def create_balance_group(
        uow: IUnitOfWork, group_data: BalanceGroupCreateSchema
    ) -> BalanceGroupResponseSchema:
        new_group = await uow.balance_groups.add_one(data=group_data.model_dump())

        if new_group is None:
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_BALANCE_GROUP)

        return BalanceGroupResponseSchema.model_validate(new_group)

    @staticmethod
    async def update_balance_group_by_id(
        uow: IUnitOfWork, group_id: int, group_data: BalanceGroupUpdateSchema
    ) -> BalanceGroupResponseSchema:
        updated_group = await uow.balance_groups.edit_one(
            id=group_id, data=group_data.model_dump(exclude_unset=True)
        )

        if updated_group is None:
            raise NotFoundError(Messages.BALANCE_GROUP_NOT_FOUND)

        return BalanceGroupResponseSchema.model_validate(updated_group)

    @staticmethod
    async def delete_balance_group_by_id(uow: IUnitOfWork, group_id: int) -> None:
        # balances in this group aren't blocked or deleted — group_id is
        # ON DELETE SET NULL, so they simply become ungrouped
        deleted_group = await uow.balance_groups.delete_one(_id=group_id)

        if deleted_group is None:
            raise NotFoundError(Messages.BALANCE_GROUP_NOT_FOUND)
