from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from app.schemas.common import ErrorResponse
from app.schemas.relationships import (
    EmployeeSkillList,
    EmployeeSkillRead,
    EmployeeSkillWrite,
)
from app.services.relationship_service import EmployeeSkillService

router = APIRouter(
    prefix="/employees/{employee_id}/skills",
    tags=["employee skills"],
)
service = EmployeeSkillService()

EmployeePath = Annotated[
    str,
    Path(pattern=r"^EMP[0-9]{3,}$", examples=["EMP001"]),
]
SkillPath = Annotated[
    str,
    Path(pattern=r"^SK[0-9]{3,}$", examples=["SK001"]),
]


@router.get(
    "",
    response_model=EmployeeSkillList,
    summary="List an employee's skills",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def list_employee_skills(employee_id: EmployeePath) -> dict:
    return service.list(employee_id)


@router.put(
    "/{skill_id}",
    response_model=EmployeeSkillRead,
    summary="Create or replace an employee skill",
    responses={
        201: {
            "model": EmployeeSkillRead,
            "description": "Employee skill created.",
        },
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def upsert_employee_skill(
    employee_id: EmployeePath,
    skill_id: SkillPath,
    payload: EmployeeSkillWrite,
    response: Response,
) -> dict:
    employee_skill, created = service.upsert(
        employee_id,
        skill_id,
        payload.level,
        payload.years_experience,
    )
    if created:
        response.status_code = status.HTTP_201_CREATED
    return employee_skill


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a skill from an employee",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def delete_employee_skill(
    employee_id: EmployeePath,
    skill_id: SkillPath,
) -> Response:
    service.delete(employee_id, skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
