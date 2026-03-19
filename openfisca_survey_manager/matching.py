"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.matching import ...
"""

import warnings
from importlib import import_module

_policy_matching = import_module("openfisca_survey_manager.policy.matching")

warnings.warn(
    "openfisca_survey_manager.matching is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.matching import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [name for name in dir(_policy_matching) if not name.startswith("_")]
globals().update({name: getattr(_policy_matching, name) for name in __all__})
