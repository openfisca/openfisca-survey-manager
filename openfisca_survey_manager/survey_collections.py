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

import codecs
import collections
import json


import logging

from .surveys import Survey
from .config import Config


log = logging.getLogger(__name__)


class SurveyCollection(object):
    """
    A collection of Surveys
    """
    config = None
    json_file_path = None
    label = None
    name = None
    surveys = list()

    def __init__(self, config_files_directory = None, label = None, name = None, json_file_path = None):
        if config_files_directory is not None:
            self.config = Config(config_files_directory = config_files_directory)

        if label is not None:
            self.label = label
        if name is not None:
            self.name = name
        if json_file_path is not None:
            self.json_file_path = json_file_path
            self.config.set("collections", self.name, self.json_file_path)
            self.config.save()
        elif self.config is not None:
            if self.config.has_option("collections", self.name):
                self.json_file_path = self.config.get("collections", self.name)



    def __repr__(self):
        header = """{}
Survey collection of {}
Contains the following surveys :
""".format(self.name, self.label)
        surveys = ["       {} : {} \n".format(survey.name, survey.label) for survey in self.surveys]
        return header + "".join(surveys)

    def dump(self, config_files_directory = None, json_file_path = None):
        if self.config is not None:
            config = self.config
        else:
            assert config_files_directory is not None, \
                'The config attribute is not set and no config_files_directory is not provided'
            self.config = Config(config_files_directory = config_files_directory)

        if json_file_path is None:
            assert self.json_file_path is not None, 'A json_file_path shoud be provided'
        else:
            self.json_file_path = json_file_path
            config.set("collections", self.name, self.json_file_path)
            config.save()

        with codecs.open(self.json_file_path, 'w', encoding = 'utf-8') as _file:
            json.dump(self.to_json(), _file, encoding = "utf-8", ensure_ascii = False, indent = 2)

    def fill_hdf(self, source_format = None, surveys = None, tables = None, overwrite = False):
        if source_format is not None:
            assert source_format in ["Rdata", "sas", "spss", "stata"], \
                "Data source format {} is unknown".format(source_format)
        if surveys is None:
            surveys = self.surveys
        for survey in surveys:
            survey.fill_hdf(source_format = source_format, tables = tables, overwrite = overwrite)
        self.dump()

    def get_survey(self, survey_name):
        return [survey for survey in self.surveys if survey.name == survey_name].pop()

    @classmethod
    def load(cls, json_file_path = None, collection = None, config_files_directory = None):
        assert config_files_directory is not None
        if json_file_path is None:
            assert collection is not None
            config = Config(config_files_directory = config_files_directory)
            json_file_path = config.get("collections", collection)

        self = cls()
        self.config = config
        with open(json_file_path, 'r') as _file:
                self_json = json.load(_file)
                self.json_file_path = json_file_path
                self.label = self_json.get('label')
                self.name = self_json.get('name')

        surveys = self_json.get('surveys')
        for survey_name, survey_json in surveys.iteritems():
            survey = Survey(name = survey_name)
            self.surveys.append(survey.create_from_json(survey_json))
        return self

    def to_json(self):
        self_json = collections.OrderedDict((
            ))
        self_json['name'] = self.name
        self_json['surveys'] = collections.OrderedDict((
            ))
        for survey in self.surveys:
            self_json['surveys'][survey.name] = survey.to_json()
        return self_json
