from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from app.schemas.common import ErrorResponse
from app.schemas.relationships import (
    ProjectRequirementList,
    ProjectRequirementRead,
    ProjectRequirementWrite,
)
from app.services.relationship_service import ProjectRequirementService

router = APIRouter(
    prefix="/projects/{project_id}/requirements",
    tags=["project requirements"],
)
service = ProjectRequirementService()

ProjectPath = Annotated[
    str,
    Path(pattern=r"^PROJ[0-9]{3,}$", examples=["PROJ001"]),
]
SkillPath = Annotated[
    str,
    Path(pattern=r"^SK[0-9]{3,}$", examples=["SK001"]),
]


@router.get(
    "",
    response_model=ProjectRequirementList,
    summary="List a project's skill requirements",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def list_project_requirements(project_id: ProjectPath) -> dict:
    return service.list(project_id)


@router.put(
    "/{skill_id}",
    response_model=ProjectRequirementRead,
    summary="Create or replace a project skill requirement",
    responses={
        201: {
            "model": ProjectRequirementRead,
            "description": "Project requirement created.",
        },
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def upsert_project_requirement(
    project_id: ProjectPath,
    skill_id: SkillPath,
    payload: ProjectRequirementWrite,
    response: Response,
) -> dict:
    requirement, created = service.upsert(
        project_id,
        skill_id,
        payload.min_level,
        payload.priority,
    )
    if created:
        response.status_code = status.HTTP_201_CREATED
    return requirement


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a skill requirement from a project",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def delete_project_requirement(
    project_id: ProjectPath,
    skill_id: SkillPath,
) -> Response:
    service.delete(project_id, skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
