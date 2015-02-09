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
import codecs
import collections
import json
import pkg_resources

from ConfigParser import SafeConfigParser


from .surveys import Survey
from .tables import Table

openfisca_france_data_location = pkg_resources.get_distribution('openfisca-france-data').location
default_config_files_directory = os.path.join(openfisca_france_data_location)


class SurveyCollection(object):
    """
    A collection of Surveys
    """
    label = None
    name = None
    surveys = list()

    def __init__(self, name = None, label = None):
        if label is not None:
            self.label = label
        if name is not None:
            self.name = name

    def __repr__(self):
        header = """{}
Survey collection of {}
Contains the following surveys :
""".format(self.name, self.label)
        surveys = ["       {} : {} \n".format(survey.name, survey.label) for _, survey in self.surveys]
        return header + "".join(surveys)

    def dump(self, file_path = None, collection = None, config_files_directory = None):
        if file_path is None:
            assert collection is not None
            file_path = self.config.get("collections", collection)

        with codecs.open(file_path, 'w', encoding = 'utf-8') as _file:
            json.dump(self.to_json(), _file, encoding = "utf-8", ensure_ascii = False, indent = 2)

    def fill_hdf(self, source_format = None, surveys = None):
        if source_format is not None:
            assert source_format in ["Rdata", "sas", "spss", "stata"], \
                "Data source format {} is unknown".format(source_format)
        if surveys is None:
            surveys = self.surveys
        for survey in surveys:
            for source_format in ['stata', 'sas', 'spss', 'Rdata']:
                files = "{}_files".format(source_format)
                for data_file in survey.informations.get(files, []):
                    TODO
                    name = data_file.rstrip('.sas7bdat')
                    table = Table(name = name, survey = survey, label = name)
                    print table.name
                    print table.informations

            return

            for table in survey.tables:
                if source_format == "Rdata":
                    survey.fill_hdf_from_Rdata(table)
                if source_format == "sas":
                    survey.fill_hdf_from_sas(table)
                if source_format == "spss":
                    survey.fill_hdf_from_spss(table)
                if source_format == "stata":
                    survey.fill_hdf_from_stata(table)

    @classmethod
    def load(cls, file_path = None, collection = None, config_files_directory = None):

        if config_files_directory is None:
            config_files_directory = default_config_files_directory
        if file_path is None:
            assert collection is not None
            self = cls()
            print config_files_directory
            self.set_config_files_directory(config_files_directory = config_files_directory)
            print self.config
            print self.config.items('collections')
            file_path = self.config.get("collections", collection)
            with open(file_path, 'r') as _file:
                self_json = json.load(_file)
                self.name = self_json.get('name')
                self.label = self_json.get('label')
        with open(file_path, 'r') as _file:
            self_json = json.load(_file)
            self = cls(name=self_json.get('name'), label=self_json.get('label'))

        surveys = self_json.get('surveys')
        for survey_name, survey_json in surveys.iteritems():
            survey = Survey(name=survey_name)
            self.surveys.append(survey.create_from_json(survey_json))
        return self

    def to_json(self):
        self_json = collections.OrderedDict((
            ))
        self_json['name'] = self.name
        self_json['surveys'] = collections.OrderedDict((
            ))
        for name, survey in self.surveys.iteritems():
            self_json['surveys'][name] = survey.to_json()
        return self_json

    def set_config_files_directory(self, config_files_directory = None):
        if config_files_directory is None:
            config_files_directory = default_config_files_directory

        parser = SafeConfigParser()
        config_local_ini = os.path.join(config_files_directory, 'config_local.ini')
        config_ini = os.path.join(config_files_directory, 'config.ini')
        parser.read([config_ini, config_local_ini])
        self.config = parser
