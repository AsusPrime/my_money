from datetime import datetime
from decimal import Decimal

import httpx
import pycountry

from src.common.constants import RATE_CLIENT_HTTP_TIMEOUT_SECONDS


class FiatRateClient:
    BASE_URL = "https://api.frankfurter.dev/v1"

    async def get_current(
        self, *, currency_ticker: str, base_currency_ticker: str
    ) -> Decimal:
        return await self._fetch(
            path="latest",
            currency_ticker=currency_ticker,
            base_currency_ticker=base_currency_ticker,
        )

    async def get_historical(
        self, *, currency_ticker: str, base_currency_ticker: str, rate_at: datetime
    ) -> Decimal:
        return await self._fetch(
            path=rate_at.strftime("%Y-%m-%d"),
            currency_ticker=currency_ticker,
            base_currency_ticker=base_currency_ticker,
        )

    async def ticker_exists(self, *, currency_ticker: str) -> bool:
        return pycountry.currencies.get(alpha_3=currency_ticker.upper()) is not None

    async def _fetch(
        self, *, path: str, currency_ticker: str, base_currency_ticker: str
    ) -> Decimal:
        async with httpx.AsyncClient(timeout=RATE_CLIENT_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{self.BASE_URL}/{path}",
                params={"from": currency_ticker, "to": base_currency_ticker},
            )
        response.raise_for_status()
        rate = response.json()["rates"][base_currency_ticker]
        return Decimal(str(rate))
