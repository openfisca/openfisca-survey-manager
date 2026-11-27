"""Public home for ``set_table_in_survey`` (insert a dataframe as a survey table).

Moved from ``tests.input_dataframe_generator`` (which required
``openfisca_country_template`` through ``tests/__init__``): downstream data
pipelines (not just tests) rely on it to register their produced tables in a
collection, so it belongs in the public API.
"""

import configparser
import logging
from pathlib import Path

from openfisca_core import periods

from openfisca_survey_manager.configuration.paths import (
    default_config_files_directory,
    openfisca_survey_manager_location,
)
from openfisca_survey_manager.core.dataset import SurveyCollection
from openfisca_survey_manager.core.survey import Survey

log = logging.getLogger(__name__)


def set_table_in_survey(
    input_dataframe,
    entity,
    period,
    collection,
    survey_name,
    survey_label=None,
    table_label=None,
    table_name=None,
    config_files_directory=default_config_files_directory,
    source_format=None,
    parquet_file=None,
):
    period = periods.period(period)
    if table_name is None:
        table_name = entity + "_" + str(period)
    if table_label is None:
        table_label = f"Input data for entity {entity} at period {period}"

    # Ensure config_files_directory is a Path
    config_files_directory = Path(config_files_directory)

    try:
        survey_collection = SurveyCollection.load(collection=collection, config_files_directory=config_files_directory)
    except (configparser.NoOptionError, configparser.NoSectionError, FileNotFoundError) as e:
        log.warning(f"set_table_in_survey falling back for collection {collection}: {e}")
        # Always use the provided config_files_directory if available, otherwise fallback to project-relative test data
        fallback_dir = Path(openfisca_survey_manager_location) / "openfisca_survey_manager" / "tests" / "data_files"
        config_dir = config_files_directory if config_files_directory else fallback_dir
        survey_collection = SurveyCollection(
            name=collection,
            config_files_directory=config_dir,
        )

    try:
        survey = survey_collection.get_survey(survey_name)
    except AssertionError:
        log.info(f"Survey {survey_name} does not exist, it will be created.")
        survey = Survey(
            name=survey_name,
            label=survey_label or None,
            survey_collection=survey_collection,
        )

    if survey.hdf5_file_path is None and survey.parquet_file_path is None:
        config = survey.survey_collection.config
        directory_path = Path(config.get("data", "output_directory"))
        if not directory_path.is_dir():
            log.warning(f"{directory_path} who should be the data directory does not exist: we create the directory")
            directory_path.mkdir(parents=True, exist_ok=True)
        if source_format is None:
            survey.hdf5_file_path = directory_path / (survey.name + ".h5")
        elif source_format == "parquet":
            survey.parquet_file_path = directory_path / survey.name
            if not survey.parquet_file_path.is_dir():
                log.warning(
                    f"{survey.parquet_file_path} who should be the parquet data directory does not exist: "
                    "we create the directory"
                )
                survey.parquet_file_path.mkdir(parents=True, exist_ok=True)

    assert (survey.hdf5_file_path is not None) or (survey.parquet_file_path is not None)
    if source_format == "parquet" and parquet_file is None:
        parquet_file = Path(survey.parquet_file_path) / (table_name + ".parquet")
    survey.insert_table(label=table_label, name=table_name, dataframe=input_dataframe, parquet_file=parquet_file)
    # If a survey with save name exist it will be overwritten
    survey_collection.surveys = [
        kept_survey for kept_survey in survey_collection.surveys if kept_survey.name != survey_name
    ]
    survey_collection.surveys.append(survey)
    collections_directory = Path(survey_collection.config.get("collections", "collections_directory"))
    assert (
        collections_directory.is_dir()
    ), f"""{collections_directory} who should be the collections' directory does not exist.
Fix the option collections_directory in the collections section of your config file."""
    collection_json_path = collections_directory / f"{collection}.json"
    survey_collection.dump(json_file_path=collection_json_path)
