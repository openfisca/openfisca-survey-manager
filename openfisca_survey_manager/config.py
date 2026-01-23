import configparser
from pathlib import Path


class Config(configparser.ConfigParser):
    config_ini = None

    def __init__(self, config_files_directory=None):
        configparser.ConfigParser.__init__(self)
        if config_files_directory is not None:
            config_ini = Path(config_files_directory) / "config.ini"
            assert config_ini.exists(), f"{config_ini} is not a valid path"
            self.config_ini = config_ini
            self.read([config_ini])

    def save(self):
        assert self.config_ini, "configuration file path is not defined"
        assert self.config_ini.exists()
        config_file = open(self.config_ini, "w")
        self.write(config_file)
        config_file.close()
