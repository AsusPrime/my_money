import os

# colima mounts the docker socket in a way the Testcontainers "Reaper" sidecar can't
# handle (fails on container start) — disable it, must happen before testcontainers is imported.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.community.postgres import PostgresContainer

from src.models import Base


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16", driver="asyncpg", dbname="my_money_test") as pg:
        yield pg


@pytest.fixture
async def session(postgres_container: PostgresContainer) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(postgres_container.get_connection_url())

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with async_session() as s:
        yield s

    await engine.dispose()
