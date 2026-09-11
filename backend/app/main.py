from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.db.graph import graph_db
from app.schemas.common import HealthResponse
from app.services.readiness_service import ReadinessChecker


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application.state.readiness = ReadinessChecker()
    try:
        yield
    finally:
        await application.state.readiness.close()
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
            "name": "dashboard",
            "description": "Authenticated workspace counts and bounded capacity overview.",
        },
        {
            "name": "project activity",
            "description": "Admin-only history of project and staffing changes.",
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
                "Project management, skill-gap analysis, and staffing recommendations."
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/api/", "/health")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Check application health",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/health/ready",
    tags=["health"],
    response_model=HealthResponse,
    summary="Check dependency readiness (cached, bounded, no sensitive details)",
    responses={503: {"model": HealthResponse}},
)
async def readiness_check(request: Request):
    checks = await request.app.state.readiness.check()
    ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready"},
        headers={"Retry-After": "5"} if not ready else None,
    )


app.include_router(api_router)
app.include_router(auth_router)
