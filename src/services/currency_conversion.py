from decimal import Decimal

from src.services.currency_service import CurrencyService
from src.services.exchange_rate_service import ExchangeRateService
from src.utils.uow.unitofwork import IUnitOfWork


async def convert_amounts_to_total(
    uow: IUnitOfWork,
    amounts: dict[str, Decimal],
    base_currency_ticker: str,
    currency_service: CurrencyService = CurrencyService(),
    exchange_rate_service: ExchangeRateService = ExchangeRateService(),
) -> Decimal:
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

    return total
