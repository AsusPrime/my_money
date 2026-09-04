from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.enums.enums import AnalyticsWidgetMetricEnum, ChartTypeEnum, LedgerReportGroupByEnum
from src.models.base import Base


class AnalyticsWidget(Base):
    __tablename__ = "analytics_widgets"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, autoincrement=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    chart_type: Mapped[ChartTypeEnum] = mapped_column(String(50), nullable=False)
    group_by: Mapped[LedgerReportGroupByEnum] = mapped_column(String(50), nullable=False)
    metric: Mapped[AnalyticsWidgetMetricEnum] = mapped_column(String(50), nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    # free-form grid placement (units of grid cells, not pixels) — matches
    # react-grid-layout's LayoutItem shape {x, y, w, h} on the frontend
    grid_x: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    grid_y: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    grid_w: Mapped[int] = mapped_column(Integer, nullable=False, server_default="6")
    grid_h: Mapped[int] = mapped_column(Integer, nullable=False, server_default="4")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
