# -*- coding: utf-8 -*-


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
