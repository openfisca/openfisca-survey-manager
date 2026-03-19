"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.scenarios.reform_scenario import ...
"""

import warnings

from openfisca_survey_manager.policy.scenarios.reform_scenario import ReformScenario

warnings.warn(
    "openfisca_survey_manager.scenarios.reform_scenario is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.scenarios.reform_scenario import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ReformScenario"]
