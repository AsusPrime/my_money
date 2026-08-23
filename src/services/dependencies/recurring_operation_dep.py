from typing import Annotated

from fastapi import Depends

from src.services.recurring_operation_service import RecurringOperationService


def get_recurring_operation_service() -> RecurringOperationService:
    return RecurringOperationService()


RecurringOperationServiceDep = Annotated[
    RecurringOperationService, Depends(get_recurring_operation_service)
]
