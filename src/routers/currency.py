from fastapi import APIRouter
from fastapi import status
from loguru import logger

from src.schemas.currency import CurrencyCreateSchema
from src.schemas.currency import CurrencyListResponseSchema
from src.schemas.currency import CurrencyResponseSchema
from src.schemas.currency import CurrencyUpdateSchema
from src.services.dependencies.currency_dep import CurrencyServiceDep
from src.utils.dependencies.uow_dep import UOWDep

router = APIRouter(
    prefix="/currencies",
    tags=["Currencies"],
)


@router.get(
    "",
    response_model=CurrencyListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_currencies_api(uow: UOWDep, currency_service: CurrencyServiceDep):
    return await currency_service.get_all_currencies(uow=uow)


@router.get(
    "/{ticker}",
    response_model=CurrencyResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_currency_api(
    ticker: str, uow: UOWDep, currency_service: CurrencyServiceDep
):
    return await currency_service.get_currency_by_ticker(uow=uow, ticker=ticker)


@router.post(
    "",
    response_model=CurrencyResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_currency_api(
    body: CurrencyCreateSchema, uow: UOWDep, currency_service: CurrencyServiceDep
):
    new_currency = await currency_service.create_currency(uow=uow, currency_data=body)
    logger.info(f"Currency created: {new_currency.ticker}")
    return new_currency


@router.patch(
    "/{ticker}",
    response_model=CurrencyResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_currency_api(
    ticker: str,
    body: CurrencyUpdateSchema,
    uow: UOWDep,
    currency_service: CurrencyServiceDep,
):
    updated_currency = await currency_service.update_currency_by_ticker(
        uow=uow, ticker=ticker, currency_data=body
    )
    logger.info(f"Currency updated: {ticker}")
    return updated_currency


@router.delete(
    "/{ticker}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_currency_api(
    ticker: str, uow: UOWDep, currency_service: CurrencyServiceDep
):
    await currency_service.delete_currency_by_ticker(uow=uow, ticker=ticker)
