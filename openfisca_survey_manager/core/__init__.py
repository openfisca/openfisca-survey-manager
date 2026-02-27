# Survey, Table, SurveyCollection. Legacy modules re-export for compatibility.
# See docs/REFACTORING_PLAN.md.

from openfisca_survey_manager.core.dataset import SurveyCollection
from openfisca_survey_manager.core.survey import NoMoreDataError, Survey
from openfisca_survey_manager.core.table import Table

__all__ = ["NoMoreDataError", "Survey", "SurveyCollection", "Table"]
