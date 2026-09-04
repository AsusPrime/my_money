from sqlalchemy import func, select

from src.models import AnalyticsWidget
from src.utils.repository.repository import SQLAlchemyRepository


class AnalyticsWidgetRepository(SQLAlchemyRepository):

    model = AnalyticsWidget

    async def get_next_row_y(self) -> int:
        """New widgets get placed below everything else — the first free row
        past the bottom of the tallest existing widget."""
        stmt = select(func.coalesce(func.max(self.model.grid_y + self.model.grid_h), 0))
        res = await self.session.execute(stmt)
        return res.scalar_one()
