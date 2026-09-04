from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.schemas.common import ErrorResponse, Page
from app.schemas.skill import SkillCreate, SkillRead, SkillUpdate
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])
service = SkillService()

SkillPath = Annotated[
    str,
    Path(pattern=r"^SK[0-9]{3,}$", examples=["SK001"]),
]


@router.get(
    "",
    response_model=Page[SkillRead],
    summary="List skills",
    responses={503: {"model": ErrorResponse}},
)
def list_skills(
    search: Annotated[
        str | None,
        Query(alias="q", min_length=1, max_length=100),
    ] = None,
    category: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return service.list(search, category, limit, offset)


@router.post(
    "",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a skill",
    responses={
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def create_skill(payload: SkillCreate) -> dict:
    return service.create(payload.model_dump(mode="json"))


@router.get(
    "/{skill_id}",
    response_model=SkillRead,
    summary="Get a skill",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_skill(skill_id: SkillPath) -> dict:
    return service.get(skill_id)


@router.patch(
    "/{skill_id}",
    response_model=SkillRead,
    summary="Update a skill",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def update_skill(skill_id: SkillPath, payload: SkillUpdate) -> dict:
    return service.update(
        skill_id,
        payload.model_dump(exclude_unset=True, mode="json"),
    )


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an unlinked skill",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def delete_skill(skill_id: SkillPath) -> Response:
    service.delete(skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
