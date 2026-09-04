from app.core.exceptions import (
    ResourceAlreadyExistsError,
    ResourceInUseError,
    ResourceNotFoundError,
)
from app.repositories import employee_repository
from app.repositories.errors import DuplicateRecordError


class EmployeeService:
    @staticmethod
    def list(
        search: str | None,
        employee_status: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        normalized_search = search.strip() if search else None
        items, total = employee_repository.list_employees(
            normalized_search,
            employee_status,
            limit,
            offset,
        )
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get(employee_id: str) -> dict:
        employee = employee_repository.get_employee(employee_id)
        if employee is None:
            raise ResourceNotFoundError("Employee", employee_id)
        return employee

    @staticmethod
    def create(properties: dict) -> dict:
        employee_id = properties["employee_id"]
        if employee_repository.get_employee(employee_id) is not None:
            raise ResourceAlreadyExistsError(
                "Employee",
                "employee_id",
                employee_id,
            )
        if employee_repository.employee_email_exists(properties["email"]):
            raise ResourceAlreadyExistsError(
                "Employee",
                "email",
                properties["email"],
            )

        try:
            return employee_repository.create_employee(properties)
        except DuplicateRecordError as exc:
            raise ResourceAlreadyExistsError(
                "Employee",
                "employee_id or email",
                employee_id,
            ) from exc

    @staticmethod
    def update(employee_id: str, updates: dict) -> dict:
        employee = employee_repository.get_employee(employee_id)
        if employee is None:
            raise ResourceNotFoundError("Employee", employee_id)

        email = updates.get("email")
        if email and employee_repository.employee_email_exists(
            email,
            exclude_employee_id=employee_id,
        ):
            raise ResourceAlreadyExistsError("Employee", "email", email)

        try:
            updated_employee = employee_repository.update_employee(
                employee_id,
                updates,
            )
        except DuplicateRecordError as exc:
            raise ResourceAlreadyExistsError(
                "Employee",
                "email",
                email or employee["email"],
            ) from exc

        if updated_employee is None:
            raise ResourceNotFoundError("Employee", employee_id)
        return updated_employee

    @staticmethod
    def delete(employee_id: str) -> None:
        relationship_count = employee_repository.delete_employee(employee_id)
        if relationship_count is None:
            raise ResourceNotFoundError("Employee", employee_id)
        if relationship_count > 0:
            raise ResourceInUseError(
                "Employee",
                employee_id,
                relationship_count,
            )
