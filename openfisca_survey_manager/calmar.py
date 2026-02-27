"""Re-export for backward compatibility. Prefer: from openfisca_survey_manager.processing.weights import calmar."""

from openfisca_survey_manager.processing.weights import calmar, check_calmar

__all__ = ["calmar", "check_calmar"]
