from fastapi import FastAPI
from fastapi import Request
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.core.exceptions.exceptions import (
    AddRecordError,
    AlreadyExistsError,
    BadRequestError,
    ConflictError,
    ConnectingDbError,
    NotFoundError,
)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ConflictError)
    async def conflict_exception_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc.message)}
        )

    @app.exception_handler(NotFoundError)
    async def not_found_exception_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc.message)}
        )

    @app.exception_handler(AlreadyExistsError)
    async def already_exists_exception_handler(
        request: Request, exc: AlreadyExistsError
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc.message)}
        )

    @app.exception_handler(BadRequestError)
    async def bad_request_exception_handler(request: Request, exc: BadRequestError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc.message)},
        )

    @app.exception_handler(AddRecordError)
    async def add_record_exception_handler(request: Request, exc: AddRecordError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc.message)}
        )

    @app.exception_handler(ConnectingDbError)
    async def connecting_db_exception_handler(request: Request, exc: ConnectingDbError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc.message)},
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_exception_handler(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Database integrity error"},
        )
