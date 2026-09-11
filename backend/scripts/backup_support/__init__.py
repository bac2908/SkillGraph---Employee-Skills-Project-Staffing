"""Local recovery tooling. No network/file mutations happen on import."""


class BackupError(Exception):
    """Operator-safe error: messages must never contain credentials or row data."""
