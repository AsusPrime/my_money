from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from src.models.base import Base


class BalanceGroup(Base):
    __tablename__ = "balance_groups"

    account = relationship("Account", back_populates="balance_groups")
    balances = relationship("Balance", back_populates="group")

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
