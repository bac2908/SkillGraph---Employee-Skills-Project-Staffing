from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.schemas.common import ErrorResponse, Page
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeRead,
    EmployeeStatus,
    EmployeeUpdate,
)
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])
service = EmployeeService()

EmployeePath = Annotated[
    str,
    Path(pattern=r"^EMP[0-9]{3,}$", examples=["EMP001"]),
]


@router.get(
    "",
    response_model=Page[EmployeeRead],
    summary="List employees",
    responses={503: {"model": ErrorResponse}},
)
def list_employees(
    search: Annotated[
        str | None,
        Query(alias="q", min_length=1, max_length=100),
    ] = None,
    employee_status: Annotated[
        EmployeeStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return service.list(
        search,
        employee_status.value if employee_status else None,
        limit,
        offset,
    )


@router.post(
    "",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an employee",
    responses={
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def create_employee(payload: EmployeeCreate) -> dict:
    return service.create(payload.model_dump(mode="json"))


@router.get(
    "/{employee_id}",
    response_model=EmployeeRead,
    summary="Get an employee",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_employee(employee_id: EmployeePath) -> dict:
    return service.get(employee_id)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeRead,
    summary="Update an employee",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def update_employee(
    employee_id: EmployeePath,
    payload: EmployeeUpdate,
) -> dict:
    return service.update(
        employee_id,
        payload.model_dump(exclude_unset=True, mode="json"),
    )


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an unlinked employee",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def delete_employee(employee_id: EmployeePath) -> Response:
    service.delete(employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
