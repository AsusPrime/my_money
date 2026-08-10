from typing import Annotated

from fastapi import Depends

from src.utils.uow.unitofwork import IUnitOfWork
from src.utils.uow.unitofwork import UnitOfWork


def get_uow() -> IUnitOfWork:
    return UnitOfWork()


UOWDep = Annotated[IUnitOfWork, Depends(get_uow)]
