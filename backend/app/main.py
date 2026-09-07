from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.db.graph import graph_db
from app.schemas.common import HealthResponse


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        graph_db.close()


app = FastAPI(
    title="SkillGraph API",
    description="Employee skill-gap analysis and project staffing API.",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "health",
            "description": "Application liveness.",
        },
        {
            "name": "employees",
            "description": "Employee profile management.",
        },
        {
            "name": "skills",
            "description": "Skill catalogue management.",
        },
        {
            "name": "employee skills",
            "description": "Employee proficiency and experience management.",
        },
        {
            "name": "projects",
            "description": (
                "Project management, skill-gap analysis, and staffing "
                "recommendations."
            ),
        },
        {
            "name": "project assignments",
            "description": (
                "Employee staffing with a strict 100% total allocation cap."
            ),
        },
        {
            "name": "project requirements",
            "description": "Required project skills, levels, and priorities.",
        },
    ],
)

register_exception_handlers(app)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Check application health",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
