"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.policy import ...
or from openfisca_survey_manager.policy.simulation_builder import ...
"""

import warnings

from openfisca_survey_manager.policy.simulation_builder import (
    SimulationBuilder,
    diagnose_variable_mismatch,
)

warnings.warn(
    "openfisca_survey_manager.simulation_builder is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy import ... "
    "or from openfisca_survey_manager.policy.simulation_builder import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "SimulationBuilder",
    "diagnose_variable_mismatch",
]
