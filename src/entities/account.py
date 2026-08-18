from src.models import Account
from src.utils.uow.unitofwork import IUnitOfWork


class AccountEntity:
    def __init__(self, account: Account, uow: IUnitOfWork) -> None:
        self._account = account
        self._uow = uow

    async def archive(self) -> None:
        self._account.is_archived = True
