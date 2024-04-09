import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


openfisca_survey_manager_location = Path(__file__).parent.parent


# Hack for use at the CASD (shared user)
# Use taxipp/.config/ directory if exists as default_config_files_directory
try:
    import taxipp
    taxipp_location = Path(taxipp.__file__).parent.parent
    default_config_files_directory = os.path.join(taxipp_location, '.config', 'openfisca-survey-manager')
except ImportError:
    taxipp_location = None

if taxipp_location is None or not os.path.exists(default_config_files_directory):
    default_config_files_directory = None


# Hack for using with france-data on a CI or locally
try:
    import openfisca_france_data
    france_data_location = Path(openfisca_france_data.__file__).parent.parent
    from xdg import BaseDirectory
    default_config_files_directory = BaseDirectory.save_config_path('openfisca-survey-manager')
except ImportError:
    france_data_location = None

if france_data_location is None or not os.path.exists(default_config_files_directory):
    default_config_files_directory = None

# Run CI when testing openfisca-survey-manager for example GitHub Actions
test_config_files_directory = os.path.join(
    openfisca_survey_manager_location,
    'openfisca_survey_manager',
    'tests',
    'data_files',
    )

with open(os.path.join(test_config_files_directory, 'config_template.ini')) as file:
    config_ini = file.read()

config_ini = config_ini.format(location = openfisca_survey_manager_location)
try:
    with open(os.path.join(test_config_files_directory, 'config.ini'), "w+") as file:
        file.write(config_ini)
except PermissionError:
    log.debug(f"config.ini can't be written in the test config files directory{test_config_files_directory}")
    pass

# GitHub Actions test
is_in_ci = 'CI' in os.environ
private_run_with_data = False

if is_in_ci and default_config_files_directory is None:
    if "CI_RUNNER_TAGS" in os.environ:
        private_run_with_data = (
            ("data-in" in os.environ["CI_RUNNER_TAGS"])
            # or ("data-out" in os.environ["CI_RUNNER_TAGS"])
            )
    if not private_run_with_data:
        default_config_files_directory = test_config_files_directory

if default_config_files_directory is None:
    from xdg import BaseDirectory
    default_config_files_directory = BaseDirectory.save_config_path('openfisca-survey-manager')

    log.debug(f'Using default_config_files_directory = {default_config_files_directory}')
