from abc import ABC
from abc import abstractmethod

from src.db.database import async_session
from src.repositories.account import AccountRepository
from src.repositories.balance import BalanceRepository
from src.repositories.currency import CurrencyRepository
from src.repositories.ledger import LedgerRepository


class IUnitOfWork(ABC):
    """
    Interface for UnitOfWork pattern, which ensures atomicity of database operations.
    This interface is designed to handle multiple repositories in a single transaction.
    """

    accounts: AccountRepository
    currencies: CurrencyRepository
    balances: BalanceRepository
    ledgers: LedgerRepository

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, *args):
        pass

    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass


class UnitOfWork(IUnitOfWork):
    """
    Concrete implementation of the UnitOfWork interface.
    Manages database transactions and ensures all changes are committed or rolled back atomically.
    """

    def __init__(self):
        self.session_factory = async_session

    async def __aenter__(self):
        self.session = self.session_factory()
        self.accounts = AccountRepository(self.session)
        self.currencies = CurrencyRepository(self.session)
        self.balances = BalanceRepository(self.session)
        self.ledgers = LedgerRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()
        if exc_type is not None:
            raise exc_val.with_traceback(exc_tb)

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
