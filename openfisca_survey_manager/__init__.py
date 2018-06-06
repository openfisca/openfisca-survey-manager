# -*- coding: utf-8 -*-

import os
import pkg_resources
from xdg import BaseDirectory

is_travis = 'TRAVIS' in os.environ

if is_travis:
    default_config_files_directory = os.path.join(
        pkg_resources.get_distribution('openfisca-survey-manager').location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )
else:
    default_config_files_directory = BaseDirectory.save_config_path('openfisca-survey-manager')
