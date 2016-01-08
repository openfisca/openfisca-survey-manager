#! /usr/bin/env python
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Build or update a collection from raw surveys data/"""


import argparse
import ConfigParser
import datetime
import logging
import os
import sys


from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey


app_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
app_name = os.path.splitext(os.path.basename(__file__))[0]
config_files_directory = app_dir
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
    surveys_name = data_directory_path_by_survey_suffix.keys()
    assert surveys_name is not None, "A list of surveys to process is needed"

    if replace_metadata:
        survey_collection = SurveyCollection(
            name = collection_name, config_files_directory = config_files_directory)
    else:
        try:
            survey_collection = SurveyCollection.load(
                collection = collection_name, config_files_directory = config_files_directory)
        except ConfigParser.NoOptionError:
            survey_collection = SurveyCollection(
                name = collection_name, config_files_directory = config_files_directory)

    for survey_suffix, data_directory_path in data_directory_path_by_survey_suffix.iteritems():
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
            _format for _format in data_file_by_format.keys()
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', default = os.path.join(app_dir, 'raw_data.ini'),
        help = "path of configuration file", nargs = '?')
    parser.add_argument('-c', '--collection', help = "name of collection to build or update", required = True)
    parser.add_argument('-d', '--replace-data', action = 'store_true', default = False,
        help = "erase existing survey data HDF5 file (instead of failing when HDF5 file already exists)")
    parser.add_argument('-m', '--replace-metadata', action = 'store_true', default = False,
        help = "erase existing collection metadata JSON file (instead of just adding new surveys)")
    parser.add_argument('-s', '--survey', help = 'name of survey to build or update (default = all)')
    parser.add_argument('-v', '--verbose', action = 'store_true', default = False, help = "increase output verbosity")
    args = parser.parse_args()
    logging.basicConfig(level = logging.DEBUG if args.verbose else logging.WARNING, stream = sys.stdout)

    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(args.config)
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
