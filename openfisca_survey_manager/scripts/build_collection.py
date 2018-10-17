#! /usr/bin/env python
# -*- coding: utf-8 -*-


"""Build or update a collection from raw surveys data/"""


import argparse
import configparser
import datetime
import logging
import os
import pkg_resources
import shutil
import sys


from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey
from openfisca_survey_manager import default_config_files_directory

config_files_directory = default_config_files_directory
app_name = os.path.splitext(os.path.basename(__file__))[0]
log = logging.getLogger(app_name)


def add_survey_to_collection(survey_name = None, survey_collection = None, sas_files = [], stata_files = []):
    assert survey_collection is not None
    overwrite = True
    label = survey_name

    for test_survey in survey_collection.surveys:
        if test_survey.name == survey_name:
            survey = survey_collection.get_survey(survey_name)
    if overwrite:
        survey = Survey(
            name = survey_name,
            label = label,
            sas_files = sas_files,
            stata_files = stata_files,
            survey_collection = survey_collection,
            )
    else:
        survey = survey_collection.get(survey_name)
        survey.label = label
        survey.informations.update({
            "sas_files": sas_files,
            "stata_files": stata_files,
            })
    survey_collection.surveys = [
        kept_survey for kept_survey in survey_collection.surveys if kept_survey.name != survey_name
        ]
    survey_collection.surveys.append(survey)


def create_data_file_by_format(directory_path = None):
    '''
    Browse subdirectories to extract stata and sas files
    '''
    stata_files = []
    sas_files = []

    for root, subdirs, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if os.path.basename(file_name).endswith(".dta"):
                log.info("Found stata file {}".format(file_path))
                stata_files.append(file_path)
            if os.path.basename(file_name).endswith(".sas7bdat"):
                log.info("Found sas file {}".format(file_path))
                sas_files.append(file_path)
    return {'stata': stata_files, 'sas': sas_files}


def build_survey_collection(collection_name = None, replace_metadata = False, replace_data = False,
        data_directory_path_by_survey_suffix = None, source_format = 'sas'):

    assert collection_name is not None
    assert data_directory_path_by_survey_suffix is not None
    surveys_name = list(data_directory_path_by_survey_suffix.keys())
    assert surveys_name is not None, "A list of surveys to process is needed"

    if replace_metadata:
        survey_collection = SurveyCollection(
            name = collection_name, config_files_directory = config_files_directory)
    else:
        try:
            survey_collection = SurveyCollection.load(
                collection = collection_name, config_files_directory = config_files_directory)
        except configparser.NoOptionError:
            survey_collection = SurveyCollection(
                name = collection_name, config_files_directory = config_files_directory)

    for survey_suffix, data_directory_path in data_directory_path_by_survey_suffix.items():
        assert os.path.isdir(data_directory_path), '{} is not a valid directory path'.format(data_directory_path)

        data_file_by_format = create_data_file_by_format(data_directory_path)
        survey_name = '{}_{}'.format(collection_name, survey_suffix)
        add_survey_to_collection(
            survey_name = survey_name,
            survey_collection = survey_collection,
            sas_files = data_file_by_format.get('sas'),
            stata_files = data_file_by_format.get('stata'),
            )

        valid_source_format = [
            _format for _format in list(data_file_by_format.keys())
            if data_file_by_format.get((_format))
            ]
        log.info("Valid source formats are: {}".format(valid_source_format))
        source_format = valid_source_format[0]
        log.info("Using the following format: {}".format(source_format))
        collections_directory = survey_collection.config.get('collections', 'collections_directory')
        assert os.path.isdir(collections_directory), """{} who should be the collections' directory does not exist.
Fix the option collections_directory in the collections section of your config file.""".format(collections_directory)
        collection_json_path = os.path.join(collections_directory, "{}.json".format(collection_name))
        survey_collection.dump(json_file_path = collection_json_path)
        surveys = [survey for survey in survey_collection.surveys if survey.name.endswith(str(survey_suffix))]
        survey_collection.fill_hdf(source_format = source_format, surveys = surveys, overwrite = replace_data)
    return survey_collection


def check_template_config_files():
    raw_data_ini_path = os.path.join(config_files_directory, 'raw_data.ini')
    config_ini_path = os.path.join(config_files_directory, 'config.ini')
    raw_data_template_ini_path = os.path.join(config_files_directory, 'raw_data_template.ini')
    config_template_ini_path = os.path.join(config_files_directory, 'config_template.ini')

    if os.path.exists(config_files_directory):
        config_files_do_not_exist = not(os.path.exists(raw_data_ini_path) and os.path.exists(config_ini_path))
        templates_config_files_do_not_exist = not(
            os.path.exists(raw_data_template_ini_path) and os.path.exists(config_template_ini_path))

        if config_files_do_not_exist:
            if templates_config_files_do_not_exist:
                log.info("Creating configuration template files in {}".format(config_files_directory))
                template_files = [
                    'raw_data_template.ini', 'config_template.ini'
                    ]
                templates_config_files_directory = os.path.join(
                    pkg_resources.get_distribution('openfisca-survey-manager').location,
                    'openfisca_survey_manager',
                    'config_files_templates'
                    )
                for template_file in template_files:
                    shutil.copy(
                        os.path.join(templates_config_files_directory, template_file),
                        os.path.join(config_files_directory, template_file),
                        )
            print("Rename and fill the template files in {}".format(config_files_directory))
            return False
    else:
        os.makedirs(config_files_directory)
        return check_template_config_files()

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--collection', help = "name of collection to build or update", required = True)
    parser.add_argument('-d', '--replace-data', action = 'store_true', default = False,
        help = "erase existing survey data HDF5 file (instead of failing when HDF5 file already exists)")
    parser.add_argument('-m', '--replace-metadata', action = 'store_true', default = False,
        help = "erase existing collection metadata JSON file (instead of just adding new surveys)")
    parser.add_argument('-s', '--survey', help = 'name of survey to build or update (default = all)')
    parser.add_argument('-v', '--verbose', action = 'store_true', default = False, help = "increase output verbosity")
    args = parser.parse_args()
    logging.basicConfig(level = logging.DEBUG if args.verbose else logging.WARNING, stream = sys.stdout)
    if not check_template_config_files():
        return

    config_parser = configparser.SafeConfigParser()
    config_parser.read(os.path.join(config_files_directory, 'raw_data.ini'))
    assert config_parser.has_section(args.collection), 'Unkwnown collection'
    data_directory_path_by_survey_suffix = dict(config_parser.items(args.collection))
    if args.survey is not None:
        assert args.survey in data_directory_path_by_survey_suffix, 'Unknown survey data directory for {}'.format(
            args.collection)
        data_directory_path_by_survey_suffix = {
            args.survey: data_directory_path_by_survey_suffix[args.survey],
            }

    start_time = datetime.datetime.now()
    build_survey_collection(collection_name = args.collection,
        data_directory_path_by_survey_suffix = data_directory_path_by_survey_suffix,
        replace_metadata = args.replace_metadata, replace_data = args.replace_data, source_format = 'sas')

    log.info("The program has been executed in {}".format(datetime.datetime.now() - start_time))

    return 0


if __name__ == "__main__":
    sys.exit(main())
