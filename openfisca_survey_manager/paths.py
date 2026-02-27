"""Re-export for backward compatibility.

Prefer: from openfisca_survey_manager.configuration.paths import ...
"""

from openfisca_survey_manager.configuration.paths import (
    config_ini,
    default_config_files_directory,
    is_in_ci,
    openfisca_survey_manager_location,
    private_run_with_data,
    test_config_files_directory,
)

__all__ = [
    "config_ini",
    "default_config_files_directory",
    "is_in_ci",
    "openfisca_survey_manager_location",
    "private_run_with_data",
    "test_config_files_directory",
]
