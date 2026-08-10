from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_postgres_connection(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"PostgreSQL connection check failed: {e}")
        return False
