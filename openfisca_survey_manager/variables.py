"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy.variables import ...
"""

import warnings
from importlib import import_module

_policy_variables = import_module("openfisca_survey_manager.policy.variables")

warnings.warn(
    "openfisca_survey_manager.variables is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.variables import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [name for name in dir(_policy_variables) if not name.startswith("_")]
globals().update({name: getattr(_policy_variables, name) for name in __all__})
