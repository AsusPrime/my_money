from loguru import logger
from sqlalchemy.exc import IntegrityError

from src.core.exceptions.exceptions import AddRecordError, ConflictError
from src.core.exceptions.exceptions import AlreadyExistsError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.schemas.currency import CurrencyCreateSchema
from src.schemas.currency import CurrencyListResponseSchema
from src.schemas.currency import CurrencyResponseSchema
from src.schemas.currency import CurrencyUpdateSchema
from src.utils.uow.unitofwork import IUnitOfWork


class CurrencyService:

    @staticmethod
    async def get_all_currencies(uow: IUnitOfWork) -> CurrencyListResponseSchema:
        currencies = await uow.currencies.find_all()

        return CurrencyListResponseSchema(
            items=[CurrencyResponseSchema.model_validate(a) for a in currencies]
        )

    @staticmethod
    async def get_currency_by_ticker(
        uow: IUnitOfWork, ticker: str
    ) -> CurrencyResponseSchema:
        currency = await uow.currencies.find_one_or_none(ticker=ticker)

        if currency is None:
            logger.warning(f"Currency {ticker} not found")
            raise NotFoundError(Messages.CURRENCY_NOT_FOUND)

        return CurrencyResponseSchema.model_validate(currency)

    @staticmethod
    async def create_currency(
        uow: IUnitOfWork, currency_data: CurrencyCreateSchema
    ) -> CurrencyResponseSchema:
        existing_currency = await uow.currencies.find_one_or_none(ticker=currency_data.ticker)
        if existing_currency:
            logger.warning(f"Currency {currency_data.ticker} already exist")
            raise AlreadyExistsError(Messages.CURRENCY_ALREADY_EXISTS)
        new_currency = await uow.currencies.add_one(data=currency_data.model_dump())

        if new_currency is None:
            logger.error(Messages.ERROR_FILLED_TO_ADD_NEW_CURRENCY)
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_CURRENCY)

        return CurrencyResponseSchema.model_validate(new_currency)

    @staticmethod
    async def update_currency_by_ticker(
        uow: IUnitOfWork, ticker: str, currency_data: CurrencyUpdateSchema
    ) -> CurrencyResponseSchema:
        updated_currency = await uow.currencies.edit_one(
            ticker=ticker, data=currency_data.model_dump(exclude_unset=True)
        )

        if updated_currency is None:
            logger.warning(f"Currency {ticker} not found")
            raise NotFoundError(Messages.CURRENCY_NOT_FOUND)

        return CurrencyResponseSchema.model_validate(updated_currency)

    @staticmethod
    async def delete_currency_by_ticker(uow: IUnitOfWork, ticker: str) -> None:
        try:
            deleted_currency = await uow.currencies.delete_one(ticker=ticker)
        except IntegrityError:
            raise ConflictError(Messages.CURRENCY_IN_USE)

        if deleted_currency is None:
            logger.error(f"Currency {ticker} not found")
            raise NotFoundError(Messages.CURRENCY_NOT_FOUND)

        logger.info(f"Currency {ticker} deleted")
