"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.scenarios.abstract_scenario import ...
"""

import warnings

from openfisca_survey_manager.policy.scenarios.abstract_scenario import AbstractSurveyScenario

warnings.warn(
    "openfisca_survey_manager.scenarios.abstract_scenario is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.scenarios.abstract_scenario import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["AbstractSurveyScenario"]
