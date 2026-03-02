"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.matching import ...
"""

import warnings

from openfisca_survey_manager.policy.matching import (
    nnd_hotdeck,
    nnd_hotdeck_using_feather,
    nnd_hotdeck_using_rpy2,
)

warnings.warn(
    "openfisca_survey_manager.matching is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.matching import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "nnd_hotdeck",
    "nnd_hotdeck_using_feather",
    "nnd_hotdeck_using_rpy2",
]
