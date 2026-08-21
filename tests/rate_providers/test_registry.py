import pytest

from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.enums.enums import CurrencyTypeEnum
from src.rate_providers.crypto.client import CryptoRateClient
from src.rate_providers.fiat.client import FiatRateClient
from src.rate_providers.registry import get_rate_client
from src.rate_providers.stock.client import StockRateClient


class TestGetRateClient:
    def test_fiat_resolves_to_fiat_client(self):
        assert isinstance(get_rate_client(CurrencyTypeEnum.FIAT), FiatRateClient)

    def test_crypto_resolves_to_crypto_client(self):
        assert isinstance(get_rate_client(CurrencyTypeEnum.CRYPTO), CryptoRateClient)

    def test_stock_resolves_to_stock_client(self):
        assert isinstance(get_rate_client(CurrencyTypeEnum.STOCK), StockRateClient)

    def test_raises_for_currency_type_with_no_configured_client(self):
        with pytest.raises(NotFoundError) as exc_info:
            get_rate_client(CurrencyTypeEnum.BOND)

        assert exc_info.value.message == Messages.RATE_CLIENT_NOT_FOUND
