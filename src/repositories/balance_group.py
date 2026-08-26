from src.models.balance_group import BalanceGroup
from src.utils.repository.repository import SQLAlchemyRepository


class BalanceGroupRepository(SQLAlchemyRepository):

    model = BalanceGroup
