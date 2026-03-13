"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.calmar import ...
"""

import warnings

from openfisca_survey_manager.policy.calmar import calmar, check_calmar

warnings.warn(
    "openfisca_survey_manager.calmar is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.calmar import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["calmar", "check_calmar"]
