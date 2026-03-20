"""SurveyCollection: collection of surveys (dataset orchestration)."""

from __future__ import annotations

import codecs
import collections
import configparser
import json
import logging
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

from openfisca_survey_manager.configuration.models import Config
from openfisca_survey_manager.configuration.paths import default_config_files_directory
from openfisca_survey_manager.core.survey import Survey
from openfisca_survey_manager.exceptions import SurveyConfigError

log = logging.getLogger(__name__)


class SurveyCollection:
    """A collection of Surveys."""

    name: Optional[str] = None
    label: Optional[str] = None
    json_file_path: Optional[str] = None
    surveys: List[Survey]  # set in __init__
    config: Optional[Config] = None

    def __init__(
        self,
        config_files_directory: Optional[Union[Path, str]] = default_config_files_directory,
        label: Optional[str] = None,
        name: Optional[str] = None,
        json_file_path: Optional[str] = None,
    ) -> None:
        self.name = name
        self.label = label
        self.json_file_path = json_file_path
        self.surveys = []
        log.debug(f"Initializing SurveyCollection from config file found in {config_files_directory} ..")
        config = Config(config_files_directory=config_files_directory)
        if label is not None:
            self.label = label
        if name is not None:
            self.name = name
        if json_file_path is not None:
            self.json_file_path = json_file_path
            if "collections" not in config.sections():
                config["collections"] = {}
            config.set("collections", self.name, str(self.json_file_path))
            config.save()
        elif config is not None:
            if config.has_option("collections", self.name):
                self.json_file_path = config.get("collections", self.name)
            elif config.get("collections", "collections_directory") is not None:
                self.json_file_path = str(Path(config.get("collections", "collections_directory")) / (name + ".json"))

        self.config = config

    def __repr__(self) -> str:
        header = f"""{self.name}
Survey collection of {self.label}
Contains the following surveys :
"""
        surveys = [f"       {survey.name} : {survey.label} \n" for survey in self.surveys]
        return header + "".join(surveys)

    def dump(
        self,
        config_files_directory: Optional[Union[Path, str]] = None,
        json_file_path: Optional[str] = None,
    ) -> None:
        if self.config is not None:
            config = self.config
        else:
            if config_files_directory is not None:
                pass
            else:
                config_files_directory = default_config_files_directory
            self.config = Config(config_files_directory=config_files_directory)

        if json_file_path is None:
            assert self.json_file_path is not None, "A json_file_path should be provided"
        else:
            self.json_file_path = json_file_path

        config.set("collections", self.name, str(self.json_file_path))
        config.save()
        with codecs.open(str(self.json_file_path), "w", encoding="utf-8") as _file:
            json.dump(self.to_json(), _file, ensure_ascii=False, indent=2)

    def fill_store(
        self,
        source_format: Optional[str] = None,
        surveys: Optional[List[Survey]] = None,
        tables: Optional[List[str]] = None,
        overwrite: bool = False,
        keep_original_parquet_file: bool = False,
        encoding: Optional[str] = None,
        store_format: str = "hdf5",
        categorical_strategy: str = "unique_labels",
    ) -> None:
        if surveys is None:
            surveys = self.surveys
        for survey in surveys:
            survey.fill_store(
                source_format=source_format,
                tables=tables,
                overwrite=overwrite,
                keep_original_parquet_file=keep_original_parquet_file,
                encoding=encoding,
                store_format=store_format,
                categorical_strategy=categorical_strategy,
            )
        self.dump()

    def get_survey(self, survey_name: str) -> Survey:
        available_surveys_names = [survey.name for survey in self.surveys]
        assert survey_name in available_surveys_names, (
            f"Survey {survey_name} cannot be found for survey collection {self.name}.\n"
            f"Available surveys are :{available_surveys_names}"
        )
        return [survey for survey in self.surveys if survey.name == survey_name].pop()

    @classmethod
    def load(
        cls,
        json_file_path: Optional[str] = None,
        collection: Optional[str] = None,
        config_files_directory: Optional[Union[Path, str]] = default_config_files_directory,
    ) -> SurveyCollection:
        assert Path(config_files_directory).exists()
        config = Config(config_files_directory=config_files_directory)
        if json_file_path is None:
            assert collection is not None, "A collection is needed"
            try:
                json_file_path = config.get("collections", collection)
            except (configparser.NoOptionError, configparser.NoSectionError) as error:
                msg = f"Looking for config file in {config_files_directory}"
                log.debug(msg)
                log.error(error)
                raise error
            except Exception as error:
                msg = f"Looking for config file in {config_files_directory}"
                log.debug(msg)
                log.error(error)
                raise SurveyConfigError(msg) from error

        with Path(json_file_path).open("r") as _file:
            self_json = json.load(_file)
            name = self_json["name"]

        self = cls(config_files_directory=config_files_directory, name=name)
        self.config = config
        with Path(json_file_path).open("r") as _file:
            self_json = json.load(_file)
            self.json_file_path = json_file_path
            self.label = self_json.get("label")
            self.name = self_json.get("name")

        surveys = self_json["surveys"]
        for survey_name, survey_json in surveys.items():
            survey = Survey(name=survey_name)
            self.surveys.append(survey.create_from_json(survey_json))
        return self

    def to_json(self) -> dict:
        self_json = collections.OrderedDict(())
        self_json["name"] = self.name
        self_json["surveys"] = collections.OrderedDict(())
        for survey in self.surveys:
            self_json["surveys"][survey.name] = survey.to_json()
        return self_json


def load_table(
    config_files_directory,
    variables: Optional[list] = None,
    collection: Optional[str] = None,
    survey: Optional[str] = None,
    input_data_survey_prefix: Optional[str] = None,
    data_year=None,
    table: Optional[str] = None,
    batch_size=None,
    batch_index=0,
    filter_by=None,
) -> pd.DataFrame:
    """Load table from a survey in a collection."""
    survey_collection = SurveyCollection.load(collection=collection, config_files_directory=config_files_directory)
    survey_name = survey if survey is not None else f"{input_data_survey_prefix}_{data_year}"
    survey_ = survey_collection.get_survey(survey_name)
    log.debug("Loading table %s in survey %s from collection %s", table, survey_name, collection)
    if batch_size:
        return survey_.get_values(
            table=table,
            variables=variables,
            batch_size=batch_size,
            batch_index=batch_index,
            filter_by=filter_by,
        )
    return survey_.get_values(table=table, variables=variables, filter_by=filter_by)
