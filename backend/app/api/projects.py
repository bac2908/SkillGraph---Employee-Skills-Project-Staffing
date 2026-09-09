from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.auth_dependencies import CurrentUser
from app.core.audit import AuditActor
from app.schemas.candidate_recommendation import (
    CandidateRecommendationResponse,
)
from app.schemas.common import ErrorResponse, Page
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectStatus,
    ProjectUpdate,
)
from app.schemas.skill_gap import SkillGapResponse
from app.services.candidate_recommendation_service import (
    CandidateRecommendationService,
)
from app.services.project_service import ProjectService
from app.services.skill_gap_service import SkillGapService

router = APIRouter(prefix="/projects", tags=["projects"])
project_service = ProjectService()
skill_gap_service = SkillGapService()
candidate_recommendation_service = CandidateRecommendationService()

ProjectPath = Annotated[
    str,
    Path(pattern=r"^PROJ[0-9]{3,}$", examples=["PROJ001"]),
]


@router.get(
    "",
    response_model=Page[ProjectRead],
    summary="List projects",
    responses={503: {"model": ErrorResponse}},
)
def list_projects(
    search: Annotated[
        str | None,
        Query(alias="q", min_length=1, max_length=100),
    ] = None,
    project_status: Annotated[
        ProjectStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return project_service.list(
        search,
        project_status.value if project_status else None,
        limit,
        offset,
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    responses={
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def create_project(payload: ProjectCreate, user: CurrentUser) -> dict:
    return project_service.create(
        payload.model_dump(mode="json"), actor=AuditActor.from_user(user)
    )


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Get a project",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_project(project_id: ProjectPath) -> dict:
    return project_service.get(project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Update a project",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def update_project(
    project_id: ProjectPath, payload: ProjectUpdate, user: CurrentUser
) -> dict:
    return project_service.update(
        project_id,
        payload.model_dump(exclude_unset=True, mode="json"),
        actor=AuditActor.from_user(user),
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an unlinked project",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def delete_project(project_id: ProjectPath, user: CurrentUser) -> Response:
    project_service.delete(project_id, actor=AuditActor.from_user(user))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{project_id}/skill-gap",
    response_model=SkillGapResponse,
    summary="Analyze a project's skill coverage",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_skill_gap(project_id: ProjectPath) -> dict:
    return skill_gap_service.analyze(project_id)


@router.get(
    "/{project_id}/recommendations",
    response_model=CandidateRecommendationResponse,
    summary="Recommend candidates for uncovered skills",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_candidate_recommendations(project_id: ProjectPath) -> dict:
    return candidate_recommendation_service.recommend(project_id)
