from fastapi import APIRouter

from app.api.employees import router as employees_router
from app.api.projects import router as projects_router
from app.api.skills import router as skills_router

api_router = APIRouter(prefix="/api")
api_router.include_router(employees_router)
api_router.include_router(skills_router)
api_router.include_router(projects_router)
