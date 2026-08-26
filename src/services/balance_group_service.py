from src.core.exceptions.exceptions import AddRecordError, AlreadyExistsError, NotFoundError
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
        await BalanceGroupService._ensure_name_is_free(
            uow, account_id=group_data.account_id, name=group_data.name
        )

        new_group = await uow.balance_groups.add_one(data=group_data.model_dump())

        if new_group is None:
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_BALANCE_GROUP)

        return BalanceGroupResponseSchema.model_validate(new_group)

    @staticmethod
    async def update_balance_group_by_id(
        uow: IUnitOfWork, group_id: int, group_data: BalanceGroupUpdateSchema
    ) -> BalanceGroupResponseSchema:
        if group_data.name is not None:
            existing_group = await uow.balance_groups.find_one_or_none(id=group_id)
            if existing_group is None:
                raise NotFoundError(Messages.BALANCE_GROUP_NOT_FOUND)
            await BalanceGroupService._ensure_name_is_free(
                uow,
                account_id=existing_group.account_id,
                name=group_data.name,
                exclude_id=group_id,
            )

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

    @staticmethod
    async def _ensure_name_is_free(
        uow: IUnitOfWork, *, account_id: int, name: str, exclude_id: int | None = None
    ) -> None:
        normalized = name.strip().lower()
        siblings = await uow.balance_groups.find_all(account_id=account_id)
        for sibling in siblings:
            if sibling.id == exclude_id:
                continue
            if sibling.name.strip().lower() == normalized:
                raise AlreadyExistsError(Messages.BALANCE_GROUP_ALREADY_EXISTS)
