"""Centralized exceptions for OpenFisca Survey Manager.

Use these instead of generic ValueError/TypeError where the error is
specific to survey loading, configuration, or processing.
"""


class SurveyManagerError(Exception):
    """Base exception for survey manager operations.

    Use for configuration errors, I/O failures, invalid data, or
    orchestration errors. Prefer specific subclasses when relevant.
    """

    pass


class SurveyConfigError(SurveyManagerError):
    """Raised when configuration is invalid or missing."""

    pass


class SurveyIOError(SurveyManagerError):
    """Raised when reading or writing survey data fails."""

    pass
