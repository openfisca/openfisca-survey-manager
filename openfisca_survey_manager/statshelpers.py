"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.statshelpers import ...
"""

import warnings

from openfisca_survey_manager.policy.statshelpers import (
    bottom_share,
    gini,
    kakwani,
    lorenz,
    mark_weighted_percentiles,
    pseudo_lorenz,
    top_share,
    weighted_quantiles,
    weightedcalcs_quantiles,
)

warnings.warn(
    "openfisca_survey_manager.statshelpers is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.statshelpers import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "bottom_share",
    "gini",
    "kakwani",
    "lorenz",
    "mark_weighted_percentiles",
    "pseudo_lorenz",
    "top_share",
    "weighted_quantiles",
    "weightedcalcs_quantiles",
]
