from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import DatabaseError, DataError, IntegrityError


async def global_error_handler(request: Request, call_next):
    """
    Catches errors that are not domain CustomBaseException (those are handled
    by exception_handlers.py) — HTTP, DB, and other unexpected exceptions.
    """
    try:
        return await call_next(request)
    except HTTPException as e:
        logger.error(f"HTTP error occurred: {e.status_code} - {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except IntegrityError as e:
        logger.error(f"Integrity error: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Data integrity constraint violation"},
        )
    except DataError as e:
        logger.error(f"Data error occurred: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Data type error"},
        )
    except DatabaseError as e:
        logger.error(f"Database error occurred: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error"},
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )
