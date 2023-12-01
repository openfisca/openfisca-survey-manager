"""
Test the ability to store parquet files in collections, without converting them to HDF5.
"""

import os

from openfisca_survey_manager import openfisca_survey_manager_location
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.scripts.build_collection import add_survey_to_collection

from openfisca_survey_manager.scripts.build_collection import check_template_config_files, build_survey_collection

from unittest import TestCase


class TestParquet(TestCase):
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )
    collection_name = 'test_parquet_collection'
    survey_name = 'test_parquet_survey'

    def test_add_survey_to_collection_parquet(self):
        survey_collection = SurveyCollection(name = self.collection_name)
        survey_file_path = os.path.join(self.data_dir, 'test.parquet')
        add_survey_to_collection(
            survey_name = self.survey_name,
            survey_collection = survey_collection,
            parquet_files = [survey_file_path],
            )
        ordered_dict = survey_collection.to_json()
        assert self.survey_name in list(ordered_dict['surveys'].keys())

    def test_build_collection(self):
        data_directory_path_by_survey_suffix = {
            "2020": os.path.join(self.data_dir, 'test_parquet_collection/'),
            }
        build_survey_collection(
            collection_name =self.collection_name,
            data_directory_path_by_survey_suffix = data_directory_path_by_survey_suffix,
            replace_metadata = False,
            replace_data = False,
            source_format = 'parquet',
            config_files_directory = self.data_dir,
            )

