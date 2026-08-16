from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.exceptions import ConnectingDbError
from src.core.messages.messages import Messages
from src.db.database import get_session
from src.db.postgres_db import check_postgres_connection

router = APIRouter(
    prefix="/health",
    tags=["Health check"],
)


@router.get("")
async def health_check_api(request: Request):
    logger.info("Health check endpoint was called")
    return {
        "status_code": 200,
        "version": request.app.state.app_version,
    }


@router.get("/postgres")
async def health_check_postgres_api(session: AsyncSession = Depends(get_session)):
    postgres_status = await check_postgres_connection(session=session)
    if postgres_status:
        logger.info("Successfully connected to PostgreSQL")
        return {"postgresql": "connected"}

    logger.error("Error connecting to PostgreSQL")
    raise ConnectingDbError(Messages.ERROR_CONNECTING_DATABASE)
