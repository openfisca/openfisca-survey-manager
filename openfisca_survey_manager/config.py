# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import ConfigParser


class Config(ConfigParser.SafeConfigParser):
    config_local_ini = None
    config_ini = None

    def __init__(self, config_files_directory = None):
        ConfigParser.SafeConfigParser.__init__(self)
        if config_files_directory is not None:
            config_local_ini = os.path.join(config_files_directory, 'config_local.ini')
            if os.path.exists(config_local_ini):
                self.config_local_ini = config_local_ini
            config_ini = os.path.join(config_files_directory, 'config.ini')
            if os.path.exists(config_ini):
                self.config_ini = config_ini
            self.read([config_ini, config_local_ini])

    def save(self):
        assert self.config_local_ini or self.config_ini, "configuration file paths are not defined"
        if self.config_local_ini and os.path.exists(self.config_local_ini):
            config_file = open(self.config_local_ini, 'w')
        else:
            config_file = open(self.config_ini, 'w')
        self.write(config_file)
        config_file.close()
