"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.core.survey import Survey, NoMoreDataError.
"""

from openfisca_survey_manager.core.survey import NoMoreDataError, Survey

__all__ = ["NoMoreDataError", "Survey"]
