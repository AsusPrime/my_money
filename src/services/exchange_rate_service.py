from datetime import datetime
from decimal import Decimal

from src.core.exceptions.exceptions import NotFoundError
from src.enums.enums import CurrencyTypeEnum
from src.rate_providers.registry import get_rate_client


class ExchangeRateService:
    @classmethod
    async def get_historical_rate(
        cls,
        currency_ticker: str,
        base_currency_ticker: str,
        currency_type: CurrencyTypeEnum,
        rate_at: datetime,
    ) -> Decimal:
        client = get_rate_client(currency_type)
        return await client.get_historical(
            currency_ticker=currency_ticker,
            base_currency_ticker=base_currency_ticker,
            rate_at=rate_at,
        )

    @classmethod
    async def get_current_rate(
        cls,
        currency_ticker: str,
        base_currency_ticker: str,
        currency_type: CurrencyTypeEnum,
    ) -> Decimal:
        client = get_rate_client(currency_type)
        return await client.get_current(
            currency_ticker=currency_ticker,
            base_currency_ticker=base_currency_ticker,
        )

    @classmethod
    async def ticker_exists(cls, currency_ticker: str, currency_type: CurrencyTypeEnum) -> bool:
        try:
            client = get_rate_client(currency_type)
        except NotFoundError:
            return False
        return await client.ticker_exists(currency_ticker=currency_ticker)
