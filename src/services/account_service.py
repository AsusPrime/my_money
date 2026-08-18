from loguru import logger

from src.core.exceptions.exceptions import AddRecordError, ConflictError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.entities.account import AccountEntity
from src.schemas.account import AccountCreateSchema
from src.schemas.account import AccountListResponseSchema
from src.schemas.account import AccountResponseSchema
from src.schemas.account import AccountUpdateSchema
from src.utils.uow.unitofwork import IUnitOfWork


class AccountService:

    @staticmethod
    async def get_all_accounts(uow: IUnitOfWork) -> AccountListResponseSchema:
        accounts = await uow.accounts.find_all()

        return AccountListResponseSchema(
            items=[AccountResponseSchema.model_validate(a) for a in accounts]
        )

    @staticmethod
    async def get_account_by_id(
        uow: IUnitOfWork, account_id: int
    ) -> AccountResponseSchema:
        account = await uow.accounts.find_one_or_none(id=account_id)

        if account is None:
            logger.warning(f"Account {account_id} not found")
            raise NotFoundError(Messages.ACCOUNT_NOT_FOUND)

        return AccountResponseSchema.model_validate(account)

    @staticmethod
    async def create_account(
        uow: IUnitOfWork, account_data: AccountCreateSchema
    ) -> AccountResponseSchema:
        currency = await uow.currencies.find_one_or_none(
            ticker=account_data.base_currency_ticker
        )
        if currency is None:
            logger.warning(
                f"Currency {account_data.base_currency_ticker} not found"
            )
            raise NotFoundError(Messages.CURRENCY_NOT_FOUND)

        new_account = await uow.accounts.add_one(data=account_data.model_dump())

        if new_account is None:
            logger.error(Messages.ERROR_FILLED_TO_ADD_NEW_ACCOUNT)
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_ACCOUNT)

        return AccountResponseSchema.model_validate(new_account)

    @staticmethod
    async def update_account_by_id(
        uow: IUnitOfWork, account_id: int, account_data: AccountUpdateSchema
    ) -> AccountResponseSchema:
        if account_data.base_currency_ticker:
            currency = await uow.currencies.find_one_or_none(ticker=account_data.base_currency_ticker)
            if not currency:
                logger.warning(f"Currency {account_data.base_currency_ticker} not found")
                raise NotFoundError(Messages.CURRENCY_NOT_FOUND)
        updated_account = await uow.accounts.edit_one(
            _id=account_id, data=account_data.model_dump(exclude_unset=True)
        )

        if updated_account is None:
            logger.warning(f"Account {account_id} not found")
            raise NotFoundError(Messages.ACCOUNT_NOT_FOUND)

        return AccountResponseSchema.model_validate(updated_account)

    @staticmethod
    async def archive_account_by_id(uow: IUnitOfWork, account_id: int) -> None:
        account_to_archive = await uow.accounts.find_one_or_none(id=account_id)

        if not account_to_archive:
            logger.error(f"Account {account_id} not found")
            raise NotFoundError(Messages.ACCOUNT_NOT_FOUND)
        
        balances = await uow.balances.find_all_unarchived_by_account_id(account_id=account_id)

        if balances:
            logger.warning(f"Account {account_id} has unarchived balances")
            raise ConflictError(Messages.ACCOUNT_HAS_ACTIVE_BALANCES)
        
        account = AccountEntity(account=account_to_archive, uow=uow)

        try:
            await account.archive()
            logger.info(f"Account {account_id} archived")
        except Exception as e:
            logger.error(f"{e}")
            raise e
