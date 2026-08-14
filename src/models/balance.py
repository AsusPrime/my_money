from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from src.models.base import Base


class Balance(Base):
    __tablename__ = "balances"

    account = relationship("Account", back_populates="balances")
    analytics = relationship(
        "Analytic", back_populates="balance", cascade="all, delete-orphan"
    )

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

    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
