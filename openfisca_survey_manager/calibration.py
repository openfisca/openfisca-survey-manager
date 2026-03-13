"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.calibration import ...
"""

import warnings

from openfisca_survey_manager.policy.calibration import Calibration

warnings.warn(
    "openfisca_survey_manager.calibration is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.calibration import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Calibration"]
