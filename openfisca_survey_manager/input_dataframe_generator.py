"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.tests.input_dataframe_generator import ...
"""

import warnings

from openfisca_survey_manager.tests.input_dataframe_generator import (
    build_input_dataframe_from_test_case,
    make_input_dataframe_by_entity,
    random_data_generator,
    randomly_init_variable,
    set_table_in_survey,
)

warnings.warn(
    "openfisca_survey_manager.input_dataframe_generator is deprecated and will be removed in a future version. "
    "Prefer: from openfisca_survey_manager.tests.input_dataframe_generator import ...",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "build_input_dataframe_from_test_case",
    "make_input_dataframe_by_entity",
    "random_data_generator",
    "randomly_init_variable",
    "set_table_in_survey",
]
