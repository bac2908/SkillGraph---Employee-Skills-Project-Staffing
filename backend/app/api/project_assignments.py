from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from app.schemas.common import ErrorResponse
from app.schemas.relationships import (
    ProjectAssignmentList,
    ProjectAssignmentRead,
    ProjectAssignmentWrite,
)
from app.services.relationship_service import ProjectAssignmentService

router = APIRouter(
    prefix="/projects/{project_id}/assignments",
    tags=["project assignments"],
)
service = ProjectAssignmentService()

ProjectPath = Annotated[
    str,
    Path(pattern=r"^PROJ[0-9]{3,}$", examples=["PROJ001"]),
]
EmployeePath = Annotated[
    str,
    Path(pattern=r"^EMP[0-9]{3,}$", examples=["EMP001"]),
]


@router.get(
    "",
    response_model=ProjectAssignmentList,
    summary="List a project's employee assignments",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def list_project_assignments(project_id: ProjectPath) -> dict:
    return service.list(project_id)


@router.put(
    "/{employee_id}",
    response_model=ProjectAssignmentRead,
    summary="Create or replace a project assignment",
    responses={
        201: {
            "model": ProjectAssignmentRead,
            "description": "Project assignment created.",
        },
        404: {"model": ErrorResponse},
        409: {
            "model": ErrorResponse,
            "description": "The employee would exceed 100% allocation.",
        },
        503: {"model": ErrorResponse},
    },
)
def upsert_project_assignment(
    project_id: ProjectPath,
    employee_id: EmployeePath,
    payload: ProjectAssignmentWrite,
    response: Response,
) -> dict:
    assignment, created = service.upsert(
        project_id,
        employee_id,
        payload.role,
        payload.allocation,
    )
    if created:
        response.status_code = status.HTTP_201_CREATED
    return assignment


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an employee from a project",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def delete_project_assignment(
    project_id: ProjectPath,
    employee_id: EmployeePath,
) -> Response:
    service.delete(project_id, employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
