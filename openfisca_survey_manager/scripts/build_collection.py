"""Build or update a collection from raw surveys data."""

import argparse
import configparser
import datetime
import logging
import os
from pathlib import Path
import pdb
import re
import shutil
import sys

from openfisca_survey_manager.paths import (
    default_config_files_directory,
    openfisca_survey_manager_location,
)
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey

app_name = os.path.splitext(os.path.basename(__file__))[0]
log = logging.getLogger(app_name)


def add_survey_to_collection(
    survey_name=None,
    survey_collection=None,
    sas_files=None,
    stata_files=None,
    csv_files=None,
    parquet_files=None,
):
    if sas_files is None:
        sas_files = []
    if stata_files is None:
        stata_files = []
    if csv_files is None:
        csv_files = []
    if parquet_files is None:
        parquet_files = []

    assert survey_collection is not None
    overwrite = True
    label = survey_name

    for test_survey in survey_collection.surveys:
        if test_survey.name == survey_name:
            survey = survey_collection.get_survey(survey_name)
    if overwrite:
        survey = Survey(
            name=survey_name,
            label=label,
            csv_files=csv_files,
            sas_files=sas_files,
            stata_files=stata_files,
            parquet_files=parquet_files,
            survey_collection=survey_collection,
        )
    else:
        survey = survey_collection.get(survey_name)
        survey.label = label
        survey.informations.update(
            {
                "csv_files": csv_files,
                "sas_files": sas_files,
                "stata_files": stata_files,
                "parquet_files": parquet_files,
            }
        )
    survey_collection.surveys = [
        kept_survey
        for kept_survey in survey_collection.surveys
        if kept_survey.name != survey_name
    ]
    survey_collection.surveys.append(survey)


def create_data_file_by_format(directory_path=None):
    """Browse subdirectories to extract stata and sas files."""
    stata_files = []
    sas_files = []
    csv_files = []
    parquet_files = []

    for root, _subdirs, files in os.walk(directory_path):
        for file_name in files:
            file_path = Path(root, file_name)
            if os.path.basename(file_name).endswith(".csv"):
                log.info(f"Found csv file {file_path}")
                csv_files.append(file_path)
            if os.path.basename(file_name).endswith(".dta"):
                log.info(f"Found stata file {file_path}")
                stata_files.append(file_path)
            if os.path.basename(file_name).endswith(".sas7bdat"):
                log.info(f"Found sas file {file_path}")
                sas_files.append(file_path)
            if os.path.basename(file_name).endswith(".parquet"):
                log.info(f"Found parquet file {file_path}")
                relative = file_name[file_name.find(directory_path) :]
                if ("/" in relative or "\\" in relative) and re.match(
                    r".*-\d$", file_name
                ):
                    # Keep only the folder name if parquet files are in subfolders and name contains "-<number>"
                    file_path = os.path.dirname(file_name)
                parquet_files.append(file_path)
    return {
        "csv": csv_files,
        "stata": stata_files,
        "sas": sas_files,
        "parquet": parquet_files,
    }


def build_survey_collection(
    config_files_directory: str,
    collection_name=None,
    replace_metadata=False,
    replace_data=False,
    data_directory_path_by_survey_suffix=None,
    source_format="sas",
    keep_original_parquet_file=False,
    encoding=None,
):
    assert collection_name is not None
    assert data_directory_path_by_survey_suffix is not None
    surveys_name = list(data_directory_path_by_survey_suffix.keys())
    assert surveys_name is not None, "A list of surveys to process is needed"

    if replace_metadata:
        survey_collection = SurveyCollection(
            name=collection_name, config_files_directory=config_files_directory
        )
    else:
        try:
            survey_collection = SurveyCollection.load(
                collection=collection_name,
                config_files_directory=config_files_directory,
            )
        except configparser.NoOptionError:
            survey_collection = SurveyCollection(
                name=collection_name, config_files_directory=config_files_directory
            )

    for (
        survey_suffix,
        data_directory_path,
    ) in data_directory_path_by_survey_suffix.items():
        assert Path(data_directory_path).is_dir(), (
            f"{data_directory_path} is not a valid directory path"
        )

        data_file_by_format = create_data_file_by_format(data_directory_path)
        survey_name = f"{collection_name}_{survey_suffix}"
        # Save the originals files list in the survey collection
        add_survey_to_collection(
            survey_name=survey_name,
            survey_collection=survey_collection,
            csv_files=data_file_by_format.get("csv"),
            sas_files=data_file_by_format.get("sas"),
            stata_files=data_file_by_format.get("stata"),
            parquet_files=data_file_by_format.get("parquet"),
        )

        valid_source_format = [
            _format
            for _format in list(data_file_by_format.keys())
            if data_file_by_format.get(_format)
        ]
        log.info(f"Valid source formats are: {valid_source_format}")
        source_format = valid_source_format[0]
        log.info(f"Using the following format: {source_format}")
        collections_directory = survey_collection.config.get(
            "collections", "collections_directory"
        )
        if Path(collections_directory).is_dir() is False:
            log.info(
                f"{collections_directory} who should be the collections' directory does not exist. Creating directory."
            )
            Path(collections_directory).mkdir()
        collection_json_path = os.path.join(
            collections_directory, f"{collection_name}.json"
        )
        survey_collection.dump(json_file_path=collection_json_path)
        surveys = []
        for survey in survey_collection.surveys:
            if survey.name.endswith(str(survey_suffix)) and survey.name.startswith(
                collection_name
            ):
                surveys.append(survey)
        survey_collection.fill_store(
            source_format=source_format,
            surveys=surveys,
            overwrite=replace_data,
            keep_original_parquet_file=keep_original_parquet_file,
            encoding=encoding,
        )
    return survey_collection


def check_template_config_files(config_files_directory: str):
    """Create template config files if they do not exist."""
    raw_data_ini_path = Path(config_files_directory, "raw_data.ini")
    config_ini_path = Path(config_files_directory, "config.ini")
    raw_data_template_ini_path = os.path.join(
        config_files_directory, "raw_data_template.ini"
    )
    config_template_ini_path = os.path.join(
        config_files_directory, "config_template.ini"
    )

    if Path(config_files_directory).exists():
        config_files_do_not_exist = not (
            Path(raw_data_ini_path).exists() and Path(config_ini_path).exists()
        )
        templates_config_files_do_not_exist = not (
            Path(raw_data_template_ini_path).exists()
            and Path(config_template_ini_path).exists()
        )

        if config_files_do_not_exist:
            if templates_config_files_do_not_exist:
                log.info(
                    f"Creating configuration template files in {config_files_directory}"
                )
                template_files = ["raw_data_template.ini", "config_template.ini"]
                templates_config_files_directory = os.path.join(
                    openfisca_survey_manager_location,
                    "openfisca_survey_manager",
                    "config_files_templates",
                )
                for template_file in template_files:
                    shutil.copy(
                        Path(templates_config_files_directory, template_file),
                        Path(config_files_directory, template_file),
                    )
            return False
    else:
        Path(config_files_directory).mkdir(parents=True, exist_ok=True)
        return check_template_config_files(config_files_directory)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--collection",
        help="name of collection to build or update",
        required=True,
    )
    parser.add_argument(
        "-d",
        "--replace-data",
        action="store_true",
        default=False,
        help="erase existing survey data HDF5 file (instead of failing when HDF5 file already exists)",
    )
    parser.add_argument(
        "-m",
        "--replace-metadata",
        action="store_true",
        default=False,
        help="erase existing collection metadata JSON file (instead of just adding new surveys)",
    )
    parser.add_argument(
        "-p",
        "--path",
        help=f"path to the config files directory (default = {default_config_files_directory})",
    )
    parser.add_argument(
        "-s", "--survey", help="name of survey to build or update (default = all)"
    )
    parser.add_argument(
        "-k",
        "--keep_original_parquet_file",
        action="store_true",
        default=False,
        help="Keep original and point to original parquet files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="increase output verbosity",
    )
    parser.add_argument("-e", "--encoding", default=None, help="encoding to be used")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING, stream=sys.stdout
    )

    config_files_directory = args.path or default_config_files_directory

    if not check_template_config_files(config_files_directory=config_files_directory):
        return None

    config_parser = configparser.ConfigParser()
    config_parser.read(Path(config_files_directory, "raw_data.ini"))
    assert config_parser.has_section(args.collection), (
        f"{args.collection} is an unkown collection. Please add a section to raw_data.ini configuration file"
    )
    data_directory_path_by_survey_suffix = dict(config_parser.items(args.collection))
    if args.survey is not None:
        assert args.survey in data_directory_path_by_survey_suffix, (
            f"Unknown survey data directory for {args.collection}"
        )
        data_directory_path_by_survey_suffix = {
            args.survey: data_directory_path_by_survey_suffix[args.survey],
        }

    start_time = datetime.datetime.now()

    try:
        build_survey_collection(
            collection_name=args.collection,
            data_directory_path_by_survey_suffix=data_directory_path_by_survey_suffix,
            replace_metadata=args.replace_metadata,
            replace_data=args.replace_data,
            source_format="sas",
            config_files_directory=config_files_directory,
            keep_original_parquet_file=args.keep_original_parquet_file,
            encoding=args.encoding,
        )
    except Exception as e:
        log.info(e)
        pdb.post_mortem(sys.exc_info()[2])
        raise

    log.info(f"The program has been executed in {datetime.datetime.now() - start_time}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
