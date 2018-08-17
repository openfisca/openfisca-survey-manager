# -*- coding: utf-8 -*-


# Hack to for use at the CASD (shared user)
# Use taxipp/.config/ directory if exists as default_config_files_directory

import logging
import os
import pkg_resources


log = logging.getLogger(__name__)

try:
    taxipp_location = pkg_resources.get_distribution('taxipp').location
    default_config_files_directory = os.path.join(taxipp_location, '.config', 'openfisca-survey-manager')
except pkg_resources.DistributionNotFound:
    default_config_files_directory = None

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
