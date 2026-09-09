from app.core.audit import AuditActor
from app.core.exceptions import (
    AllocationExceededError,
    ResourceNotFoundError,
)
from app.repositories import (
    employee_repository,
    employee_skill_repository,
    project_assignment_repository,
    project_repository,
    project_requirement_repository,
    skill_repository,
)


def _require_employee(employee_id: str) -> None:
    if employee_repository.get_employee(employee_id) is None:
        raise ResourceNotFoundError("Employee", employee_id)


def _require_project(project_id: str) -> None:
    if not project_repository.project_exists(project_id):
        raise ResourceNotFoundError("Project", project_id)


def _require_skill(skill_id: str) -> None:
    if skill_repository.get_skill(skill_id) is None:
        raise ResourceNotFoundError("Skill", skill_id)


class EmployeeSkillService:
    @staticmethod
    def list(employee_id: str) -> dict:
        _require_employee(employee_id)
        items = employee_skill_repository.list_employee_skills(employee_id)
        return {"items": items, "total": len(items)}

    @staticmethod
    def upsert(
        employee_id: str,
        skill_id: str,
        level: int,
        years_experience: float,
    ) -> tuple[dict, bool]:
        _require_employee(employee_id)
        _require_skill(skill_id)
        return employee_skill_repository.upsert_employee_skill(
            employee_id,
            skill_id,
            level,
            years_experience,
        )

    @staticmethod
    def delete(employee_id: str, skill_id: str) -> None:
        _require_employee(employee_id)
        _require_skill(skill_id)
        deleted = employee_skill_repository.delete_employee_skill(
            employee_id,
            skill_id,
        )
        if not deleted:
            raise ResourceNotFoundError(
                "Employee skill",
                f"{employee_id}/{skill_id}",
            )


class ProjectAssignmentService:
    @staticmethod
    def list(project_id: str) -> dict:
        _require_project(project_id)
        items = project_assignment_repository.list_project_assignments(project_id)
        return {"items": items, "total": len(items)}

    @staticmethod
    def upsert(
        project_id: str,
        employee_id: str,
        role: str,
        allocation: int,
        *,
        actor: AuditActor,
    ) -> tuple[dict, bool]:
        _require_project(project_id)
        _require_employee(employee_id)
        result = project_assignment_repository.upsert_project_assignment(
            project_id,
            employee_id,
            role,
            allocation,
            actor=actor,
        )
        if result.allocation_exceeded:
            raise AllocationExceededError(
                employee_id,
                project_id,
                result.allocated_elsewhere,
                allocation,
            )
        if result.assignment is None:
            raise ResourceNotFoundError("Project", project_id)
        return result.assignment, result.created

    @staticmethod
    def delete(project_id: str, employee_id: str, *, actor: AuditActor) -> None:
        _require_project(project_id)
        _require_employee(employee_id)
        deleted = project_assignment_repository.delete_project_assignment(
            project_id,
            employee_id,
            actor=actor,
        )
        if not deleted:
            raise ResourceNotFoundError(
                "Project assignment",
                f"{project_id}/{employee_id}",
            )


class ProjectRequirementService:
    @staticmethod
    def list(project_id: str) -> dict:
        _require_project(project_id)
        items = project_requirement_repository.list_project_requirements(project_id)
        return {"items": items, "total": len(items)}

    @staticmethod
    def upsert(
        project_id: str,
        skill_id: str,
        min_level: int,
        priority: str,
        *,
        actor: AuditActor,
    ) -> tuple[dict, bool]:
        _require_project(project_id)
        _require_skill(skill_id)
        return project_requirement_repository.upsert_project_requirement(
            project_id,
            skill_id,
            min_level,
            priority,
            actor=actor,
        )

    @staticmethod
    def delete(project_id: str, skill_id: str, *, actor: AuditActor) -> None:
        _require_project(project_id)
        _require_skill(skill_id)
        deleted = project_requirement_repository.delete_project_requirement(
            project_id,
            skill_id,
            actor=actor,
        )
        if not deleted:
            raise ResourceNotFoundError(
                "Project requirement",
                f"{project_id}/{skill_id}",
            )
