"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.coicop import ...
"""

import warnings
from importlib import import_module

_policy_coicop = import_module("openfisca_survey_manager.policy.coicop")

warnings.warn(
    "openfisca_survey_manager.coicop is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.coicop import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [name for name in dir(_policy_coicop) if not name.startswith("_")]
globals().update({name: getattr(_policy_coicop, name) for name in __all__})
