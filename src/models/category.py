from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from src.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    ledgers = relationship("Ledger", back_populates="category")

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
