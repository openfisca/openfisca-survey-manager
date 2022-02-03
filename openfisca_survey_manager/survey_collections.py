
import codecs
import collections
import json
import os

import logging


from openfisca_survey_manager import default_config_files_directory
from openfisca_survey_manager.surveys import Survey
from openfisca_survey_manager.config import Config


log = logging.getLogger(__name__)


class SurveyCollection(object):
    """A collection of Surveys"""
    config = None
    json_file_path = None
    label = None
    name = None
    surveys = list()

    def __init__(self, config_files_directory = default_config_files_directory, label = None, name = None, json_file_path = None):

        log.debug("Initializing SurveyCollection from config file found in {} ..".format(config_files_directory))
        config = Config(config_files_directory = config_files_directory)
        if label is not None:
            self.label = label
        if name is not None:
            self.name = name
        if json_file_path is not None:
            self.json_file_path = json_file_path
            if 'collections' not in config.sections():
                config["collections"] = dict()
            config.set("collections", self.name, self.json_file_path)
            config.save()
        elif config is not None:
            if config.has_option("collections", self.name):
                self.json_file_path = config.get("collections", self.name)
            elif config.get("collections", 'collections_directory') is not None:
                self.json_file_path = os.path.join(
                    config.get("collections", 'collections_directory'),
                    name + '.json',
                    )

        self.config = config

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
            if config_files_directory is not None:
                pass
            else:
                config_files_directory = default_config_files_directory
            self.config = Config(config_files_directory = config_files_directory)

        if json_file_path is None:
            assert self.json_file_path is not None, 'A json_file_path shoud be provided'
        else:
            self.json_file_path = json_file_path

        config.set("collections", self.name, self.json_file_path)
        config.save
        config.save()
        with codecs.open(self.json_file_path, 'w', encoding = 'utf-8') as _file:
            json.dump(self.to_json(), _file, ensure_ascii = False, indent = 2)

    def fill_hdf(self, source_format = None, surveys = None, tables = None, overwrite = False):
        if source_format is not None:
            assert source_format in ["csv", "Rdata", "sas", "spss", "stata"], \
                "Data source format {} is unknown".format(source_format)
        if surveys is None:
            surveys = self.surveys
        for survey in surveys:
            survey.fill_hdf(source_format = source_format, tables = tables, overwrite = overwrite)
        self.dump()

    def get_survey(self, survey_name):
        available_surveys_names = [survey.name for survey in self.surveys]
        assert survey_name in available_surveys_names, \
            'Survey {} cannot be found for survey collection {}.\nAvailable surveys are :{}'.format(
                survey_name, self.name, available_surveys_names)
        return [survey for survey in self.surveys if survey.name == survey_name].pop()

    @classmethod
    def load(cls, json_file_path = None, collection = None, config_files_directory = default_config_files_directory):
        assert os.path.exists(config_files_directory)
        if json_file_path is None:
            assert collection is not None, "A collection is needed"
            config = Config(config_files_directory = config_files_directory)
            try:
                json_file_path = config.get("collections", collection)
            except Exception as error:
                log.debug("Looking for congi file in {}".format(config_files_directory))
                log.error(error)
                raise

        with open(json_file_path, 'r') as _file:
            self_json = json.load(_file)
            name = self_json.get('name')

        self = cls(name = name)
        self.config = config
        with open(json_file_path, 'r') as _file:
            self_json = json.load(_file)
            self.json_file_path = json_file_path
            self.label = self_json.get('label')
            self.name = self_json.get('name')

        surveys = self_json.get('surveys')
        for survey_name, survey_json in surveys.items():
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
