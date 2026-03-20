"""Backward-compatibility wrapper for legislation helpers.

Use ``openfisca_survey_manager.policy.legislation_asof`` as canonical import path.
"""

from openfisca_survey_manager.policy.legislation_asof import (
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
