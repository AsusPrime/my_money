from decimal import Decimal

from loguru import logger

from src.core.exceptions.exceptions import AddRecordError, ConflictError, NotFoundError
from src.core.messages.messages import Messages
from src.entities.balance import BalanceEntity
from src.models import Balance
from src.schemas.balance import BalanceAmountsResponseSchema, BalanceCreateSchema, BalanceListResponseSchema, BalanceResponseSchema, BalanceTotalResponseSchema, BalanceUpdateSchema
from src.services.account_service import AccountService
from src.services.currency_service import CurrencyService
from src.services.exchange_rate_service import ExchangeRateService
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
    async def get_balance_amounts(
        uow: IUnitOfWork, balance_id: int
    ) -> BalanceAmountsResponseSchema:
        balance = await uow.balances.find_one_or_none(id=balance_id)

        if balance is None:
            logger.warning(f"Balance {balance_id} not found")
            raise NotFoundError(Messages.BALANCE_NOT_FOUND)

        balance_entity = BalanceEntity(balance=balance, uow=uow)
        amounts = await balance_entity.get_amounts()

        return BalanceAmountsResponseSchema(amounts=amounts)

    @staticmethod
    async def get_balance_total(
        uow: IUnitOfWork,
        balance_id: int,
        account_service: AccountService = AccountService(),
        currency_service: CurrencyService = CurrencyService(),
        exchange_rate_service: ExchangeRateService = ExchangeRateService(),
    ) -> BalanceTotalResponseSchema:
        balance = await uow.balances.find_one_or_none(id=balance_id)

        if balance is None:
            logger.warning(f"Balance {balance_id} not found")
            raise NotFoundError(Messages.BALANCE_NOT_FOUND)

        account = await account_service.get_account_by_id(uow=uow, account_id=balance.account_id)
        base_currency_ticker = account.base_currency_ticker

        balance_entity = BalanceEntity(balance=balance, uow=uow)
        amounts = await balance_entity.get_amounts()

        total = Decimal("0")
        for currency_ticker, amount in amounts.items():
            if currency_ticker == base_currency_ticker:
                total += amount
                continue

            currency = await currency_service.get_currency_by_ticker(uow=uow, ticker=currency_ticker)
            rate = await exchange_rate_service.get_current_rate(
                currency_ticker=currency_ticker,
                base_currency_ticker=base_currency_ticker,
                currency_type=currency.currency_type,
            )
            total += amount * rate

        return BalanceTotalResponseSchema(total=total, currency_ticker=base_currency_ticker)

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
