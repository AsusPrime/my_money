from sqlalchemy import select

from src.models.recurring_operation import RecurringOperation
from src.utils.repository.repository import SQLAlchemyRepository


class RecurringOperationRepository(SQLAlchemyRepository):

    model = RecurringOperation

    async def find_all_active(self):
        stmt = select(self.model).where(self.model.is_active.is_(True))

        res = await self.session.execute(stmt)
        return res.scalars().all()  # noqa
