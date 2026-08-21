"""Registry of available rate clients, one per currency type."""

from loguru import logger

from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.enums.enums import CurrencyTypeEnum
from src.rate_providers.base import RateClient
from src.rate_providers.crypto.client import CryptoRateClient
from src.rate_providers.fiat.client import FiatRateClient
from src.rate_providers.stock.client import StockRateClient

CLIENTS: dict[CurrencyTypeEnum, RateClient] = {
    CurrencyTypeEnum.FIAT: FiatRateClient(),
    CurrencyTypeEnum.CRYPTO: CryptoRateClient(),
    CurrencyTypeEnum.STOCK: StockRateClient(),
}


def get_rate_client(currency_type: CurrencyTypeEnum) -> RateClient:
    client = CLIENTS.get(currency_type)
    if client is None:
        logger.warning(f"No rate client configured for {currency_type}")
        raise NotFoundError(Messages.RATE_CLIENT_NOT_FOUND)
    return client
