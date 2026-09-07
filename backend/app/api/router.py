from fastapi import APIRouter

from app.api.employee_skills import router as employee_skills_router
from app.api.employees import router as employees_router
from app.api.project_assignments import router as project_assignments_router
from app.api.project_requirements import router as project_requirements_router
from app.api.projects import router as projects_router
from app.api.skills import router as skills_router

api_router = APIRouter(prefix="/api")
api_router.include_router(employees_router)
api_router.include_router(employee_skills_router)
api_router.include_router(skills_router)
api_router.include_router(projects_router)
api_router.include_router(project_assignments_router)
api_router.include_router(project_requirements_router)
