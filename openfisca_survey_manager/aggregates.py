"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy import ...
or from openfisca_survey_manager.policy.aggregates import ...
"""

import warnings

from openfisca_survey_manager.policy.aggregates import AbstractAggregates

warnings.warn(
    "openfisca_survey_manager.aggregates is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy import ... "
    "or from openfisca_survey_manager.policy.aggregates import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "AbstractAggregates",
]
