from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.repositories.errors import RepositoryError

DATABASE_UNAVAILABLE_MESSAGE = "The graph database is currently unavailable."


def register_exception_handlers(app: FastAPI) -> None:
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
        __: RepositoryError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": DATABASE_UNAVAILABLE_MESSAGE},
        )
