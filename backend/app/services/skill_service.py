from app.core.exceptions import (
    ResourceAlreadyExistsError,
    ResourceInUseError,
    ResourceNotFoundError,
)
from app.repositories import skill_repository
from app.repositories.errors import DuplicateRecordError


class SkillService:
    @staticmethod
    def list(
        search: str | None,
        category: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        normalized_search = search.strip() if search else None
        normalized_category = category.strip() if category else None
        items, total = skill_repository.list_skills(
            normalized_search,
            normalized_category,
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
    def get(skill_id: str) -> dict:
        skill = skill_repository.get_skill(skill_id)
        if skill is None:
            raise ResourceNotFoundError("Skill", skill_id)
        return skill

    @staticmethod
    def create(properties: dict) -> dict:
        skill_id = properties["skill_id"]
        if skill_repository.get_skill(skill_id) is not None:
            raise ResourceAlreadyExistsError("Skill", "skill_id", skill_id)
        if skill_repository.skill_name_exists(properties["name"]):
            raise ResourceAlreadyExistsError(
                "Skill",
                "name",
                properties["name"],
            )

        try:
            return skill_repository.create_skill(properties)
        except DuplicateRecordError as exc:
            raise ResourceAlreadyExistsError(
                "Skill",
                "skill_id or name",
                skill_id,
            ) from exc

    @staticmethod
    def update(skill_id: str, updates: dict) -> dict:
        skill = skill_repository.get_skill(skill_id)
        if skill is None:
            raise ResourceNotFoundError("Skill", skill_id)

        name = updates.get("name")
        if name and skill_repository.skill_name_exists(
            name,
            exclude_skill_id=skill_id,
        ):
            raise ResourceAlreadyExistsError("Skill", "name", name)

        try:
            updated_skill = skill_repository.update_skill(skill_id, updates)
        except DuplicateRecordError as exc:
            raise ResourceAlreadyExistsError(
                "Skill",
                "name",
                name or skill["name"],
            ) from exc

        if updated_skill is None:
            raise ResourceNotFoundError("Skill", skill_id)
        return updated_skill

    @staticmethod
    def delete(skill_id: str) -> None:
        relationship_count = skill_repository.delete_skill(skill_id)
        if relationship_count is None:
            raise ResourceNotFoundError("Skill", skill_id)
        if relationship_count > 0:
            raise ResourceInUseError("Skill", skill_id, relationship_count)
