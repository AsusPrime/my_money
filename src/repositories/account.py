from src.models.account import Account
from src.utils.repository.repository import SQLAlchemyRepository


class AccountRepository(SQLAlchemyRepository):

    model = Account
