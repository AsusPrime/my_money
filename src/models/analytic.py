from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import DECIMAL, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.enums.enums import AnalyticTypeEnum, RangeEnum
from src.models import Base


class Analytic(Base):
    __tablename__ = "analytics"

    balance = relationship("Balance", back_populates="analytics")
    account = relationship("Account", back_populates="analytics")

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        autoincrement=True
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    date_range: Mapped[RangeEnum] = mapped_column(
        String(50),
        nullable=False
    )
    analytic_type: Mapped[AnalyticTypeEnum] = mapped_column(
        String(50),
        nullable=False
    )
    asset_realized_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False
    )
    asset_unrealized_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False
    )
    asset_roi: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False
    )
    fx_realized_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False
    )
    fx_unrealized_pnl: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False
    )
    fx_roi: Mapped[Decimal] = mapped_column(
        DECIMAL(20, 8),
        nullable=False
    )

    balance_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("balances.id", ondelete="CASCADE"),
        nullable=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
