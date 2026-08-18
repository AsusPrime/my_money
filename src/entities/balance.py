from decimal import Decimal

from src.core.exceptions.exceptions import ConflictError
from src.core.messages.messages import Messages
from src.models import Balance
from src.utils.uow.unitofwork import IUnitOfWork


class BalanceEntity:
    def __init__(self, balance: Balance, uow: IUnitOfWork) -> None:
        self._balance = balance
        self._uow = uow

    async def get_amounts(self) -> dict[str, Decimal]:
        return await self._uow.ledgers.get_amounts_by_balance_id(balance_id=self._balance.id)

    async def archive(self) -> None:
        self._balance.is_archived = True

    async def ensure_sufficient_funds(self, currency_ticker: str, amount: Decimal) -> None:
        amounts = await self.get_amounts()
        current = amounts.get(currency_ticker, Decimal("0"))
        if current + amount < 0:
            raise ConflictError(Messages.BALANCE_INSUFFICIENT_FUNDS)
