from typing import Annotated

from fastapi import Depends

from src.services.ledger_service import LedgerService


def get_ledger_service() -> LedgerService:
    return LedgerService()


LedgerServiceDep = Annotated[LedgerService, Depends(get_ledger_service)]
