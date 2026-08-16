from typing import Annotated

from fastapi import Depends

from src.services.balance_service import BalanceService


def get_balance_service() -> BalanceService:
    return BalanceService()


BalanceServiceDep = Annotated[BalanceService, Depends(get_balance_service)]
