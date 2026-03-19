"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.statshelpers import ...
"""

import warnings
from importlib import import_module

_policy_statshelpers = import_module("openfisca_survey_manager.policy.statshelpers")

warnings.warn(
    "openfisca_survey_manager.statshelpers is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.statshelpers import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [name for name in dir(_policy_statshelpers) if not name.startswith("_")]
globals().update({name: getattr(_policy_statshelpers, name) for name in __all__})
