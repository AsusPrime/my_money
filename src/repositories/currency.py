from src.models.currency import Currency
from src.utils.repository.repository import SQLAlchemyRepository


class CurrencyRepository(SQLAlchemyRepository):

    model = Currency
