from datetime import datetime
from decimal import Decimal

import httpx
from loguru import logger

from src.common.constants import RATE_CLIENT_HTTP_TIMEOUT_SECONDS
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages


class CryptoRateClient:
    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self._id_cache: dict[str, str] = {}

    async def get_current(
        self, *, currency_ticker: str, base_currency_ticker: str
    ) -> Decimal:
        coingecko_id = await self._resolve_id(currency_ticker)
        vs_currency = base_currency_ticker.lower()
        async with httpx.AsyncClient(timeout=RATE_CLIENT_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{self.BASE_URL}/simple/price",
                params={"ids": coingecko_id, "vs_currencies": vs_currency},
            )
        response.raise_for_status()
        rate = response.json()[coingecko_id][vs_currency]
        return Decimal(str(rate))

    async def get_historical(
        self, *, currency_ticker: str, base_currency_ticker: str, rate_at: datetime
    ) -> Decimal:
        coingecko_id = await self._resolve_id(currency_ticker)
        vs_currency = base_currency_ticker.lower()
        async with httpx.AsyncClient(timeout=RATE_CLIENT_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{self.BASE_URL}/coins/{coingecko_id}/history",
                params={"date": rate_at.strftime("%d-%m-%Y")},
            )
        response.raise_for_status()
        rate = response.json()["market_data"]["current_price"][vs_currency]
        return Decimal(str(rate))

    async def ticker_exists(self, *, currency_ticker: str) -> bool:
        try:
            await self._resolve_id(currency_ticker)
        except NotFoundError:
            return False
        return True

    async def _resolve_id(self, currency_ticker: str) -> str:
        ticker = currency_ticker.lower()
        if ticker in self._id_cache:
            return self._id_cache[ticker]

        async with httpx.AsyncClient(timeout=RATE_CLIENT_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{self.BASE_URL}/coins/markets",
                params={"vs_currency": "usd", "symbols": ticker, "order": "market_cap_desc"},
            )
        response.raise_for_status()
        results = response.json()
        if not results:
            logger.warning(f"No CoinGecko id found for {currency_ticker}")
            raise NotFoundError(Messages.COINGECKO_ID_NOT_FOUND)

        coingecko_id = results[0]["id"]
        self._id_cache[ticker] = coingecko_id
        return coingecko_id
