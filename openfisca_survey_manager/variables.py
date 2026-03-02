"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.variables import ...
"""

import warnings

from openfisca_survey_manager.policy.variables import (
    create_quantile,
    old_quantile,
    quantile,
)

warnings.warn(
    "openfisca_survey_manager.variables is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.variables import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "create_quantile",
    "old_quantile",
    "quantile",
]
