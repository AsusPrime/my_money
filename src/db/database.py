from typing import Any, AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config.config import settings
from src.core.exceptions.exceptions import ConnectingDbError
from src.core.messages.messages import Messages

engine = create_async_engine(
    settings.sqlalchemy_database_url,
    pool_size=10,
    max_overflow=10,
    pool_timeout=15,
    echo=False,
    future=True,
)

async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()

        except ConnectionRefusedError as e:
            await session.rollback()
            logger.error(f"Session rollback due to: {e}")
            raise ConnectingDbError(Messages.ERROR_CONNECTING_DATABASE)

        finally:
            await session.close()
