from typing import Annotated

from fastapi import Depends

from src.services.currency_service import CurrencyService


def get_currency_service() -> CurrencyService:
    return CurrencyService()


CurrencyServiceDep = Annotated[CurrencyService, Depends(get_currency_service)]
