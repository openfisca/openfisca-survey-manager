# -*- coding: utf-8 -*-


import os
import configparser


class Config(configparser.SafeConfigParser):
    config_ini = None

    def __init__(self, config_files_directory = None):
        configparser.SafeConfigParser.__init__(self)
        if config_files_directory is not None:
            config_ini = os.path.join(config_files_directory, 'config.ini')
            if os.path.exists(config_ini):
                self.config_ini = config_ini
            self.read([config_ini])

    def save(self):
        assert self.config_ini, "configuration file path is not defined"
        assert os.path.exists(self.config_ini)
        config_file = open(self.config_ini, 'w')
        self.write(config_file)
        config_file.close()
