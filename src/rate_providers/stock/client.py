from datetime import datetime
from decimal import Decimal


class StockRateClient:
    async def get_current(
        self, *, currency_ticker: str, base_currency_ticker: str
    ) -> Decimal:
        # TODO: GET https://api.twelvedata.com/price?symbol={currency_ticker}&apikey=...
        raise NotImplementedError

    async def get_historical(
        self, *, currency_ticker: str, base_currency_ticker: str, rate_at: datetime
    ) -> Decimal:
        # TODO: GET https://api.twelvedata.com/time_series
        #       ?symbol={currency_ticker}&start_date=...&end_date=...&apikey=...
        raise NotImplementedError
