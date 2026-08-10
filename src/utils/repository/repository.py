from abc import ABC
from abc import abstractmethod
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import RowMapping
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession


class AbstractRepository(ABC):
    @abstractmethod
    async def add_one(self, data: dict) -> RowMapping:
        raise NotImplementedError

    @abstractmethod
    async def find_all(
        self, skip: int | None, limit: int | None, **filter_by
    ) -> list[RowMapping]:
        raise NotImplementedError

    @abstractmethod
    async def find_one(self, **filter_by) -> RowMapping:
        raise NotImplementedError

    @abstractmethod
    async def find_one_or_none(self, **filter_by) -> RowMapping | None:
        raise NotImplementedError

    @abstractmethod
    async def edit_one(self, _id: int | UUID, data: dict, **filter_by) -> RowMapping:
        raise NotImplementedError

    @abstractmethod
    async def delete_one(self, _id: int | UUID, **filter_by) -> RowMapping:
        raise NotImplementedError

    @abstractmethod
    async def count_all(self, **filter_by) -> int:
        raise NotImplementedError


class SQLAlchemyRepository(AbstractRepository):
    model = None

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_one(self, data: dict) -> RowMapping | None:
        stmt = (
            insert(self.model).values(**data).returning(*self.model.__table__.columns)
        )
        res = await self.session.execute(stmt)
        result = res.fetchone()
        if result is None:
            return None
        return result._mapping  # noqa

    async def edit_one(
        self, data: dict, _id: int | UUID | None = None, **filter_by
    ) -> RowMapping | None:
        filters = {}
        if _id is not None:
            filters["id"] = _id
        filters.update(filter_by)

        if not filters:
            raise ValueError(
                f"edit_one called without filters on {self.model.__tablename__} — "
                f"this would update ALL rows. Provide _id or filter_by."
            )

        stmt = (
            update(self.model)
            .values(**data)
            .filter_by(**filters)
            .returning(*self.model.__table__.columns)
        )

        res = await self.session.execute(stmt)
        result = res.fetchone()
        if result is None:
            return None
        return result._mapping  # noqa

    async def find_all(
        self, skip: int | None = None, limit: int | None = None, **filter_by
    ) -> list[RowMapping]:
        stmt = select(self.model).filter_by(**filter_by)
        if skip is not None:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()  # noqa

    async def find_one(self, **filter_by) -> RowMapping:
        stmt = select(self.model).filter_by(**filter_by)
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def find_one_or_none(self, **filter_by) -> RowMapping | None:
        stmt = select(self.model).filter_by(**filter_by)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def delete_one(self, _id: int | UUID, **filter_by) -> RowMapping | None:
        stmt = (
            delete(self.model)
            .filter_by(id=_id, **filter_by)
            .returning(*self.model.__table__.columns)
        )
        res = await self.session.execute(stmt)
        result = res.fetchone()
        if result is None:
            return None
        return result._mapping  # noqa

    async def count_all(self, **filter_by) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filter_by)
        res = await self.session.execute(stmt)
        return res.scalar()
