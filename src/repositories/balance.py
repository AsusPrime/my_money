from sqlalchemy import select, update
from src.models import Balance
from src.utils.repository.repository import SQLAlchemyRepository


class BalanceRepository(SQLAlchemyRepository):

    model = Balance


    async def find_all_by_account_id(self, account_id: int):
        stmt = select(self.model).where(self.model.account_id == account_id)

        res = await self.session.execute(stmt)
        return res.scalars().all()  # noqa
    
    async def get_name_by_id(self, id: int) -> str | None:  # TODO: write test
        stmt = select(self.model.name).where(self.model.id == id)

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()