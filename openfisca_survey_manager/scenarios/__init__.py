"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.scenarios import ...
"""

import warnings

from openfisca_survey_manager.policy.scenarios import AbstractSurveyScenario, ReformScenario

warnings.warn(
    "openfisca_survey_manager.scenarios is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.scenarios import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["AbstractSurveyScenario", "ReformScenario"]
