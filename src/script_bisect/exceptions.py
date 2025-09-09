"""Custom exceptions for script-bisect."""

from __future__ import annotations


class ScriptBisectError(Exception):
    """Base exception for script-bisect errors."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class ParseError(ScriptBisectError):
    """Raised when there's an error parsing PEP 723 metadata."""

    pass


class GitError(ScriptBisectError):
    """Raised when there's an error with git operations."""

    pass


class ExecutionError(ScriptBisectError):
    """Raised when there's an error executing the test script."""

    pass


class ConfigurationError(ScriptBisectError):
    """Raised when there's an error with tool configuration."""

    pass


class RepositoryError(ScriptBisectError):
    """Raised when there's an error with repository operations."""

    pass
