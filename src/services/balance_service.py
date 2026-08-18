from loguru import logger

from src.core.exceptions.exceptions import AddRecordError, ConflictError, NotFoundError
from src.core.messages.messages import Messages
from src.entities.balance import BalanceEntity
from src.models import Balance
from src.schemas.balance import BalanceCreateSchema, BalanceListResponseSchema, BalanceResponseSchema, BalanceUpdateSchema
from src.utils.uow.unitofwork import IUnitOfWork


class BalanceService:

    @staticmethod
    async def get_all_balances_by_account_id(uow: IUnitOfWork, account_id: int) -> BalanceListResponseSchema:
        balances = await uow.balances.find_all_by_account_id(account_id=account_id)

        return BalanceListResponseSchema(
            items=[BalanceResponseSchema.model_validate(a) for a in balances]
        )

    @staticmethod
    async def get_balance_by_id(
        uow: IUnitOfWork, balance_id: int
    ) -> BalanceResponseSchema:
        balance = await uow.balances.find_one_or_none(id=balance_id)

        if balance is None:
            logger.warning(f"Balance {balance_id} not found")
            raise NotFoundError(Messages.BALANCE_NOT_FOUND)

        return BalanceResponseSchema.model_validate(balance)

    @staticmethod
    async def create_balance(
        uow: IUnitOfWork, balance_data: BalanceCreateSchema
    ) -> BalanceResponseSchema:
        new_balance = await uow.balances.add_one(data=balance_data.model_dump())

        if new_balance is None:
            logger.error(Messages.ERROR_FILLED_TO_ADD_NEW_BALANCE)
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_BALANCE)

        return BalanceResponseSchema.model_validate(new_balance)

    @staticmethod
    async def update_balance(  # TODO: use entity here
        uow: IUnitOfWork, balance_id: int, balance_data: BalanceUpdateSchema
    ) -> BalanceResponseSchema:
        updated_balance = await uow.balances.edit_one(
            id=balance_id, data=balance_data.model_dump(exclude_unset=True)
        )

        if updated_balance is None:
            logger.warning(f"Balance {balance_id} not found")
            raise NotFoundError(Messages.BALANCE_NOT_FOUND)

        return BalanceResponseSchema.model_validate(updated_balance)

    @staticmethod
    async def archive_balance(uow: IUnitOfWork, balance_id: int) -> None:
        balance = await uow.balances.find_one_or_none(id=balance_id)

        if not balance:
            logger.error(f"Balance {balance_id} not found")
            raise NotFoundError(Messages.BALANCE_NOT_FOUND)

        balance = BalanceEntity(balance=balance, uow=uow)

        try:
            await balance.archive()
            logger.info(f"Balance {balance_id} archived")
        except Exception as e:
            logger.error(f"{e}")
            raise e

    @staticmethod
    async def get_active_balance_by_id(uow: IUnitOfWork, balance_id: int) -> Balance:
        balance = await uow.balances.find_one_or_none(id=balance_id)

        if balance is None:
            logger.warning(f"Balance {balance_id} not found")
            raise NotFoundError(Messages.BALANCE_NOT_FOUND)

        if balance.is_archived:
            logger.warning(f"Balance {balance_id} is archived")
            raise ConflictError(Messages.BALANCE_IS_ARCHIVED)

        return balance
