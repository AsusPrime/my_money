from typing import Annotated

from fastapi import Depends

from src.services.balance_group_service import BalanceGroupService


def get_balance_group_service() -> BalanceGroupService:
    return BalanceGroupService()


BalanceGroupServiceDep = Annotated[BalanceGroupService, Depends(get_balance_group_service)]
