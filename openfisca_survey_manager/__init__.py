from importlib import metadata
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


openfisca_survey_manager_location = Path(
    metadata.distribution('openfisca-survey-manager').files[0]
    ).parent

# Hack for use at the CASD (shared user)
# Use taxipp/.config/ directory if exists as default_config_files_directory
try:
    taxipp_location = Path(metadata.distribution('taxipp').files[0]).parent
    default_config_files_directory = os.path.join(taxipp_location, '.config', 'openfisca-survey-manager')
except metadata.PackageNotFoundError:
    taxipp_location = None

if taxipp_location is None or not os.path.exists(default_config_files_directory):
    default_config_files_directory = None


# Hack for uising with france-data on a CI or locally
try:
    france_data_location = Path(metadata.distribution('openfisca-france_data').files[0]).parent
    from xdg import BaseDirectory
    default_config_files_directory = BaseDirectory.save_config_path('openfisca-survey-manager')
except metadata.PackageNotFoundError:
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
with open(os.path.join(test_config_files_directory, 'config.ini'), "w+") as file:
    file.write(config_ini)

# GitHub Actions test
is_in_ci = 'CI' in os.environ

if is_in_ci and default_config_files_directory is None:
    default_config_files_directory = test_config_files_directory

if default_config_files_directory is None:
    from xdg import BaseDirectory
    default_config_files_directory = BaseDirectory.save_config_path('openfisca-survey-manager')

    log.debug('Using default_config_files_directory = {}'.format(
        default_config_files_directory
        ))
