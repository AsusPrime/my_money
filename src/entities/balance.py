from decimal import Decimal

from src.core.exceptions.exceptions import ConflictError
from src.core.messages.messages import Messages
from src.models import Balance
from src.utils.uow.unitofwork import IUnitOfWork


class BalanceEntity:
    def __init__(self, balance: Balance, uow: IUnitOfWork) -> None:
        self.balance = balance
        self.uow = uow

    async def get_amounts(self) -> dict[str, Decimal]:
        return await self.uow.ledgers.get_amounts_by_balance_id(balance_id=self.balance.id)
    
    async def _is_empty(self) -> bool:
        amounts = await self.get_amounts()
        if not amounts:
            return True
        if sum(amounts.values()) == 0:
            return True
        return False

    async def archive(self) -> None:
        if not await self._is_empty():
            raise ConflictError(Messages.BALANCE_HAS_NONZERO_AMOUNT)

        self.balance.is_archived = True
