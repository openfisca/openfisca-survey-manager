"""Backward-compatibility wrapper for legislation helpers.

Deprecated: use ``openfisca_survey_manager.policy.legislation_asof`` instead.
"""

import warnings

warnings.warn(
    "openfisca_survey_manager.common.misc is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.policy.legislation_asof import ...",
    DeprecationWarning,
    stacklevel=2,
)

from openfisca_survey_manager.policy.legislation_asof import (  # noqa: E402
    asof,
    do_nothing,
    inflate_parameter_leaf,
    inflate_parameters,
    leaf_asof,
    parameters_asof,
    variables_asof,
)

__all__ = [
    "asof",
    "do_nothing",
    "inflate_parameter_leaf",
    "inflate_parameters",
    "leaf_asof",
    "parameters_asof",
    "variables_asof",
]
