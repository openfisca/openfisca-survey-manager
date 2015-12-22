# -*- coding: utf-8 -*-

import os
import pkg_resources


default_config_files_directory = os.path.join(
    pkg_resources.get_distribution('openfisca-survey-manager').location)
