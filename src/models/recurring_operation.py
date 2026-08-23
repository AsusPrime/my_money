from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Boolean, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from src.enums.enums import AmountModeEnum
from src.enums.enums import OperationTypeEnum
from src.enums.enums import RecurrenceIntervalEnum
from src.models.base import Base


class RecurringOperation(Base):
    __tablename__ = "recurring_operations"

    balance = relationship("Balance", back_populates="recurring_operations")
    currency = relationship("Currency", back_populates="recurring_operations")
    category = relationship("Category", back_populates="recurring_operations")

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, autoincrement=True
    )
    operation_type: Mapped[OperationTypeEnum] = mapped_column(String(50), nullable=False)
    balance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("balances.id", ondelete="CASCADE"), nullable=False
    )
    currency_ticker: Mapped[str] = mapped_column(
        String(15), ForeignKey("currencies.ticker", ondelete="RESTRICT"), nullable=False
    )
    amount_mode: Mapped[AmountModeEnum] = mapped_column(String(50), nullable=False)
    amount_value: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True
    )
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interval: Mapped[RecurrenceIntervalEnum] = mapped_column(String(50), nullable=False)

    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hour: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    minute: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
