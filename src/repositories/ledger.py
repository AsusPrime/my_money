from decimal import Decimal
from sqlalchemy import func, select

from src.models import Ledger
from src.utils.repository.repository import SQLAlchemyRepository


class LedgerRepository(SQLAlchemyRepository):

    model = Ledger

    async def get_amounts_by_balance_id(self, balance_id: int) -> dict[str, Decimal]:
        stmt = (
            select(self.model.currency_ticker, func.sum(self.model.amount))
            .group_by(self.model.currency_ticker)
            .where(self.model.balance_id == balance_id)
        )

        res = await self.session.execute(stmt)
        return dict(res.all())

    async def find_all_by_balance_id(self, balance_id: int):
        stmt = select(self.model).where(self.model.balance_id == balance_id)

        res = await self.session.execute(stmt)
        return res.scalars().all()  # noqa
