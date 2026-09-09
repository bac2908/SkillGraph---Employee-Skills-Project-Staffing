from app.core.audit import AuditActor
from app.core.exceptions import (
    ResourceAlreadyExistsError,
    ResourceInUseError,
    ResourceNotFoundError,
)
from app.repositories import project_repository
from app.repositories.errors import DuplicateRecordError


class ProjectService:
    @staticmethod
    def list(
        search: str | None,
        project_status: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        normalized_search = search.strip() if search else None
        items, total = project_repository.list_projects(
            normalized_search,
            project_status,
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
    def get(project_id: str) -> dict:
        project = project_repository.get_project(project_id)
        if project is None:
            raise ResourceNotFoundError("Project", project_id)
        return project

    @staticmethod
    def create(properties: dict, *, actor: AuditActor) -> dict:
        project_id = properties["project_id"]
        if project_repository.project_exists(project_id):
            raise ResourceAlreadyExistsError(
                "Project",
                "project_id",
                project_id,
            )

        try:
            return project_repository.create_project(properties, actor=actor)
        except DuplicateRecordError as exc:
            raise ResourceAlreadyExistsError(
                "Project",
                "project_id",
                project_id,
            ) from exc

    @staticmethod
    def update(project_id: str, updates: dict, *, actor: AuditActor) -> dict:
        project = project_repository.update_project(project_id, updates, actor=actor)
        if project is None:
            raise ResourceNotFoundError("Project", project_id)
        return project

    @staticmethod
    def delete(project_id: str, *, actor: AuditActor) -> None:
        relationship_count = project_repository.delete_project(project_id, actor=actor)
        if relationship_count is None:
            raise ResourceNotFoundError("Project", project_id)
        if relationship_count > 0:
            raise ResourceInUseError(
                "Project",
                project_id,
                relationship_count,
            )
