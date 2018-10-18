# -*- coding: utf-8 -*-


import logging
import os
import pkg_resources


log = logging.getLogger(__name__)

# Hack to for use at the CASD (shared user)
# Use taxipp/.config/ directory if exists as default_config_files_directory
try:
    taxipp_location = pkg_resources.get_distribution('taxipp').location
    default_config_files_directory = os.path.join(taxipp_location, '.config', 'openfisca-survey-manager')
except pkg_resources.DistributionNotFound:
    default_config_files_directory = None

# Travis tests
is_travis = 'TRAVIS' in os.environ
is_circleci = 'CIRCLECI' in os.environ

if is_travis or is_circleci:
    default_config_files_directory = os.path.join(
        pkg_resources.get_distribution('openfisca-survey-manager').location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )

if default_config_files_directory:
    if not os.path.exists(default_config_files_directory):
        from xdg import BaseDirectory
        default_config_files_directory = BaseDirectory.save_config_path('openfisca-survey-manager')

    log.debug('Using default_config_files_directory = {}'.format(
        default_config_files_directory
        ))
else:
    log.info('Unable to initialize default_config_files_directory')
    raise
