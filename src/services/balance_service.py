from loguru import logger

from src.core.exceptions.exceptions import AddRecordError, ConflictError, NotFoundError
from src.core.messages.messages import Messages
from src.entities.balance import BalanceEntity
from src.schemas.balance import BalanceCreateSchema, BalanceListResponseSchema, BalanceResponseSchema, BalanceUpdateSchema
from src.utils.uow.unitofwork import IUnitOfWork


class BalanceService:

    @staticmethod
    async def get_all_balances_by_account_id(uow: IUnitOfWork, account_id: int) -> BalanceListResponseSchema:
        async with uow:
            balances = await uow.balances.find_all_by_account_id(account_id=account_id)

            return BalanceListResponseSchema(
                items=[BalanceResponseSchema.model_validate(a) for a in balances]
            )

    @staticmethod
    async def get_balance_by_id(
        uow: IUnitOfWork, id: int
    ) -> BalanceResponseSchema:
        async with uow:
            balance = await uow.balances.find_one_or_none(id=id)

            if balance is None:
                logger.warning(f"Balance {id} not found")
                raise NotFoundError(Messages.BALANCE_NOT_FOUND)

            return BalanceResponseSchema.model_validate(balance)

    @staticmethod
    async def create_balance(
        uow: IUnitOfWork, balance_data: BalanceCreateSchema
    ) -> BalanceResponseSchema:
        async with uow:
            new_balance = await uow.balances.add_one(data=balance_data.model_dump())

            if new_balance is None:
                logger.error(Messages.ERROR_FILLED_TO_ADD_NEW_BALANCE)
                raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_BALANCE)

            return BalanceResponseSchema.model_validate(new_balance)

    @staticmethod
    async def update_balance(  # TODO: use entity here
        uow: IUnitOfWork, id: int, balance_data: BalanceUpdateSchema
    ) -> BalanceResponseSchema:
        async with uow:
            updated_balance = await uow.balances.edit_one(
                id=id, data=balance_data.model_dump(exclude_unset=True)
            )

            if updated_balance is None:
                logger.warning(f"Balance {id} not found")
                raise NotFoundError(Messages.BALANCE_NOT_FOUND)

            return BalanceResponseSchema.model_validate(updated_balance)

    @staticmethod
    async def archive_balance(uow: IUnitOfWork, id: int) -> None:
        async with uow:
            balance = await uow.balances.find_one_or_none(id=id)

            if not balance:
                logger.error(f"Balance {id} not found")
                raise NotFoundError(Messages.BALANCE_NOT_FOUND)

            balance = BalanceEntity(balance=balance, uow=uow)

            try:
                await balance.archive()
                logger.info(f"Balance {id} archived")
            except ConflictError as e:
                logger.warning(f"{e}")
                raise e
