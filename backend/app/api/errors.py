import logging
import sqlite3

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.repositories.auth_store import AuthError
from app.repositories.errors import RepositoryError

DATABASE_UNAVAILABLE_MESSAGE = "The graph database is currently unavailable."
logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def auth_error_handler(_: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"detail": exc.detail},
            headers={"Retry-After": "900"} if exc.status == 429 else None,
        )

    @app.exception_handler(sqlite3.Error)
    async def auth_database_error(_: Request, exc: sqlite3.Error) -> JSONResponse:
        logger.error("Authentication database unavailable (%s).", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "Dịch vụ đăng nhập tạm thời không khả dụng."},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's default response includes input values, which may be passwords.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "loc": list(error["loc"]),
                        "msg": error["msg"],
                        "type": error["type"],
                    }
                    for error in exc.errors()
                ]
            },
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        _: Request,
        exc: ResourceNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ResourceConflictError)
    async def resource_conflict_handler(
        _: Request,
        exc: ResourceConflictError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(RepositoryError)
    async def repository_error_handler(
        _: Request,
        exc: RepositoryError,
    ) -> JSONResponse:
        logger.error(
            "Graph repository operation failed.",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": DATABASE_UNAVAILABLE_MESSAGE},
        )
