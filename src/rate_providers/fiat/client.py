from datetime import datetime
from decimal import Decimal

import httpx
import pycountry

from src.common.constants import RATE_CLIENT_HTTP_TIMEOUT_SECONDS
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages


class FiatRateClient:
    LATEST_HOSTS = (
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api/v1/currencies/{currency}.json",
        "https://currency-api.pages.dev/v1/currencies/{currency}.json",
    )
    HISTORICAL_HOSTS = (
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/{currency}.json",
        "https://{date}.currency-api.pages.dev/v1/currencies/{currency}.json",
    )

    async def get_current(
        self, *, currency_ticker: str, base_currency_ticker: str
    ) -> Decimal:
        currency = currency_ticker.lower()
        urls = [host.format(currency=currency) for host in self.LATEST_HOSTS]
        return await self._fetch(
            urls=urls, currency=currency, base_currency=base_currency_ticker.lower()
        )

    async def get_historical(
        self, *, currency_ticker: str, base_currency_ticker: str, rate_at: datetime
    ) -> Decimal:
        currency = currency_ticker.lower()
        date = rate_at.strftime("%Y-%m-%d")
        urls = [host.format(date=date, currency=currency) for host in self.HISTORICAL_HOSTS]
        return await self._fetch(
            urls=urls, currency=currency, base_currency=base_currency_ticker.lower()
        )

    async def ticker_exists(self, *, currency_ticker: str) -> bool:
        return pycountry.currencies.get(alpha_3=currency_ticker.upper()) is not None

    async def _fetch(self, *, urls: list[str], currency: str, base_currency: str) -> Decimal:
        last_error: httpx.HTTPError | None = None
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=RATE_CLIENT_HTTP_TIMEOUT_SECONDS) as client:
                    response = await client.get(url)
                if response.status_code == 404:
                    raise NotFoundError(Messages.RATE_NOT_AVAILABLE_FOR_DATE)
                response.raise_for_status()
                rate = response.json()[currency][base_currency]
                return Decimal(str(rate))
            except KeyError:
                raise NotFoundError(Messages.RATE_CURRENCY_NOT_SUPPORTED) from None
            except httpx.HTTPError as e:
                last_error = e
                continue

        raise last_error
