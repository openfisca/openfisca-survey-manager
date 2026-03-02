"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.coicop import ...
"""

import warnings

from openfisca_survey_manager.policy.coicop import (
    build_coicop_level_nomenclature,
    build_raw_coicop_nomenclature,
    divisions,
    legislation_directory,
    sub_levels,
)

warnings.warn(
    "openfisca_survey_manager.coicop is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.coicop import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "build_coicop_level_nomenclature",
    "build_raw_coicop_nomenclature",
    "divisions",
    "legislation_directory",
    "sub_levels",
]
