class ApplicationError(Exception):
    """Base class for expected application errors."""


class ResourceNotFoundError(ApplicationError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} '{resource_id}' does not exist.")


class ResourceConflictError(ApplicationError):
    """Raised when a request conflicts with the current graph state."""


class ResourceAlreadyExistsError(ResourceConflictError):
    def __init__(self, resource: str, field: str, value: str) -> None:
        super().__init__(
            f"{resource} with {field} '{value}' already exists."
        )


class ResourceInUseError(ResourceConflictError):
    def __init__(
        self,
        resource: str,
        resource_id: str,
        relationship_count: int,
    ) -> None:
        super().__init__(
            f"{resource} '{resource_id}' is connected by "
            f"{relationship_count} relationship(s) and cannot be deleted."
        )
