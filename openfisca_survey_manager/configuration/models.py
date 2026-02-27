"""Configuration model (Config class from config.ini)."""

from __future__ import annotations

import configparser
import logging
from pathlib import Path
from typing import Optional, Union

log = logging.getLogger(__name__)

log = logging.getLogger(__name__)


class Config(configparser.ConfigParser):
    """Parser for config.ini; used by SurveyCollection and build scripts."""

    config_ini: Optional[Path] = None

    def __init__(
        self,
        config_files_directory: Optional[Union[Path, str]] = None,
    ) -> None:
        configparser.ConfigParser.__init__(self)
        if config_files_directory is not None:
            config_ini = Path(config_files_directory) / "config.ini"
            assert config_ini.exists(), f"{config_ini} is not a valid path"
            self.config_ini = config_ini
            self.read([config_ini])
            log.debug("Loaded config from %s", config_ini)

    def save(self) -> None:
        assert self.config_ini, "configuration file path is not defined"
        assert self.config_ini.exists()
        config_file = self.config_ini.open("w")
        self.write(config_file)
        config_file.close()
        log.debug("Saved config to %s", self.config_ini)
