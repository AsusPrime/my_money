from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from src.models.base import Base


class Account(Base):
    __tablename__ = "accounts"

    balances = relationship(
        "Balance", back_populates="account", cascade="all, delete-orphan"
    )
    analytics = relationship(
        "Analytic", back_populates="account", cascade="all, delete-orphan"
    )
    base_currency = relationship("Currency", back_populates="accounts")

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )

    base_currency_ticker: Mapped[str] = mapped_column(
        String(15), ForeignKey("currencies.ticker", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
