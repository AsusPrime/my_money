from sqlalchemy import String
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from src.enums.enums import CurrencyTypeEnum
from src.models.base import Base


class Currency(Base):
    __tablename__ = "currencies"

    accounts = relationship("Account", back_populates="base_currency")
    ledgers = relationship("Ledger", back_populates="currency")

    ticker: Mapped[str] = mapped_column(
        String(15),
        primary_key=True,
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency_type: Mapped[CurrencyTypeEnum] = mapped_column(String(50), nullable=False)
