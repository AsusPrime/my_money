from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.enums.enums import OperationTypeEnum
from src.models import Base


class Ledger(Base):
    __tablename__ = "ledgers"

    currency = relationship("Currency", back_populates="ledgers")
    category = relationship("Category", back_populates="ledgers")

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        autoincrement=True,
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operation_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    operation_type: Mapped[OperationTypeEnum] = mapped_column(
        String(50),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), nullable=False)
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency_ticker: Mapped[str] = mapped_column(
        String(15), ForeignKey("currencies.ticker", ondelete="RESTRICT"), nullable=False
    )
    balance_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("balances.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    base_currency_rate: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 8), nullable=True)
