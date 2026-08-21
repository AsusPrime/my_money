from datetime import datetime
from decimal import Decimal
from typing import Protocol


class RateClient(Protocol):
    async def get_current(
        self, *, currency_ticker: str, base_currency_ticker: str
    ) -> Decimal: ...

    async def get_historical(
        self, *, currency_ticker: str, base_currency_ticker: str, rate_at: datetime
    ) -> Decimal: ...

    async def ticker_exists(self, *, currency_ticker: str) -> bool: ...
