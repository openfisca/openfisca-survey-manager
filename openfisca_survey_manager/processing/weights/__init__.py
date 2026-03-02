# Calibration and CALMAR weight calibration. Re-exports from policy.

import warnings

from openfisca_survey_manager.policy.calibration import Calibration
from openfisca_survey_manager.policy.calmar import calmar, check_calmar

warnings.warn(
    "openfisca_survey_manager.processing.weights is deprecated for Calibration/calmar. "
    "Prefer: from openfisca_survey_manager.policy.calibration import Calibration, "
    "from openfisca_survey_manager.policy.calmar import calmar, check_calmar",
    DeprecationWarning,
    stacklevel=3,
)

__all__ = ["Calibration", "calmar", "check_calmar"]
