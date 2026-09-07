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


class AllocationExceededError(ResourceConflictError):
    def __init__(
        self,
        employee_id: str,
        project_id: str,
        allocated_elsewhere: int,
        requested: int,
    ) -> None:
        proposed_total = allocated_elsewhere + requested
        super().__init__(
            f"Employee '{employee_id}' would reach {proposed_total}% total "
            f"allocation: {allocated_elsewhere}% outside Project "
            f"'{project_id}' plus {requested}% requested. The maximum is 100%."
        )
