from fastapi import APIRouter

from app.schemas.common import ErrorResponse
from app.schemas.dashboard import DashboardRead
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
service = DashboardService()


@router.get(
    "",
    response_model=DashboardRead,
    summary="Get workspace counts and a bounded staffing overview",
    description=(
        "Global counts, up to five employees ordered by total allocation, "
        "and one default project (ACTIVE first, then project ID). "
        "Allocation includes every WORKS_ON relationship regardless of dates "
        "or project status. AVAILABLE is an employee status, not free capacity. "
        "Project search remains paginated at GET /api/projects."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_dashboard() -> dict:
    return service.overview()
