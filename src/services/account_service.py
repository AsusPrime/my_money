from loguru import logger

from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.schemas.account import AccountCreateSchema
from src.schemas.account import AccountListResponseSchema
from src.schemas.account import AccountResponseSchema
from src.schemas.account import AccountUpdateSchema
from src.utils.uow.unitofwork import IUnitOfWork


class AccountService:

    @staticmethod
    async def get_all_accounts(uow: IUnitOfWork) -> AccountListResponseSchema:
        async with uow:
            accounts = await uow.accounts.find_all()

        return AccountListResponseSchema(
            items=[AccountResponseSchema.model_validate(a) for a in accounts]
        )

    async def get_account_by_id(
        self, uow: IUnitOfWork, account_id: int
    ) -> AccountResponseSchema:
        async with uow:
            account = await uow.accounts.find_one_or_none(id=account_id)

        if account is None:
            logger.warning(f"Account {account_id} not found")
            raise NotFoundError(Messages.ACCOUNT_NOT_FOUND)

        return AccountResponseSchema.model_validate(account)

    async def create_account(
        self, uow: IUnitOfWork, account_data: AccountCreateSchema
    ) -> AccountResponseSchema:
        async with uow:
            new_account = await uow.accounts.add_one(data=account_data.model_dump())

        if new_account is None:
            logger.error(Messages.ERROR_FILLED_TO_ADD_NEW_ACCOUNT)
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_ACCOUNT)

        return AccountResponseSchema.model_validate(new_account)

    async def update_account_by_id(
        self, uow: IUnitOfWork, account_id: int, account_data: AccountUpdateSchema
    ) -> AccountResponseSchema:
        async with uow:
            updated_account = await uow.accounts.edit_one(
                _id=account_id, data=account_data.model_dump(exclude_unset=True)
            )

        if updated_account is None:
            logger.warning(f"Account {account_id} not found")
            raise NotFoundError(Messages.ACCOUNT_NOT_FOUND)

        return AccountResponseSchema.model_validate(updated_account)

    async def delete_account_by_id(self, uow: IUnitOfWork, account_id: int) -> None:
        async with uow:
            deleted_account = await uow.accounts.delete_one(_id=account_id)

        if deleted_account is None:
            logger.error(f"Account {account_id} not found")
            raise NotFoundError(Messages.ACCOUNT_NOT_FOUND)

        logger.info(f"Account {account_id} deleted")
