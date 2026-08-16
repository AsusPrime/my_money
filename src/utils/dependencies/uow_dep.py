from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends

from src.utils.uow.unitofwork import IUnitOfWork
from src.utils.uow.unitofwork import UnitOfWork


async def get_uow() -> AsyncGenerator[IUnitOfWork, None]:
    uow = UnitOfWork()
    async with uow:
        yield uow


UOWDep = Annotated[IUnitOfWork, Depends(get_uow)]
