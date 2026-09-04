class RepositoryError(RuntimeError):
    """Base class for failures while accessing the graph database."""


class DuplicateRecordError(RepositoryError):
    """Raised when a database uniqueness constraint is violated."""
