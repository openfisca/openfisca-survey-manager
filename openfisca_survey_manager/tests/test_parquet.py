"""
Test the ability to store parquet files in collections, without converting them to HDF5.
"""

import os
from pathlib import Path
import pytest
import pandas as pd
from unittest import TestCase

from openfisca_core import periods
from openfisca_survey_manager import openfisca_survey_manager_location, default_config_files_directory
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.scripts.build_collection import add_survey_to_collection
from openfisca_survey_manager.scripts.build_collection import build_survey_collection
from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario
from openfisca_survey_manager.tests import tax_benefit_system


@pytest.mark.order(after="test_write_parquet.py::test_write_parquet")
class TestParquet(TestCase):
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        "openfisca_survey_manager",
        "tests",
        "data_files",
        )
    collection_name = "test_parquet_collection"
    survey_name = "test_parquet_survey"

    def test_add_survey_to_collection_parquet(self):
        survey_collection = SurveyCollection(name=self.collection_name)
        survey_file_path = os.path.join(self.data_dir, self.collection_name)
        add_survey_to_collection(
            survey_name=self.survey_name,
            survey_collection=survey_collection,
            parquet_files=[survey_file_path],
            )
        ordered_dict = survey_collection.to_json()
        assert self.survey_name in list(ordered_dict["surveys"].keys())

    def test_build_collection(self):
        collection_name = self.collection_name
        data_directory_path_by_survey_suffix = {
            "2020": os.path.join(self.data_dir, "test_parquet_collection/"),
            }
        build_survey_collection(
            collection_name=collection_name,
            data_directory_path_by_survey_suffix=data_directory_path_by_survey_suffix,
            replace_metadata=False,
            replace_data=False,
            source_format="parquet",
            config_files_directory=self.data_dir,
            )

    def test_load_parquet(self):

        df = pd.read_parquet(
            os.path.join(self.data_dir, self.collection_name, "household.parquet")
            )
        assert len(df) == 4
        assert (df.columns == ["household_id", "rent", "household_weight"]).all()
        assert df.rent.sum() == 18700

        survey_name = 'test_parquet_collection_2020'
        survey_collection = SurveyCollection.load(
            config_files_directory=self.data_dir,
            collection=self.collection_name,
            )
        survey = survey_collection.get_survey(survey_name)
        table = survey.get_values(
            table="household", ignorecase=True
            )
        assert len(table) == 4
        assert (table.columns == ["household_id", "rent", "household_weight"]).all()
        assert table.rent.sum() == 18700

        # Create survey scenario
        survey_scenario = AbstractSurveyScenario()
        input_data_frame_by_entity = table
        survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
        survey_scenario.period = 2020
        survey_scenario.used_as_input_variables = ["rent"]
        survey_scenario.collection = self.collection_name
        period = periods.period('2020-01')
        data = {
            'collection': 'test_parquet_collection',
            'survey': 'test_parquet_collection_2020',
            'input_data_table_by_entity_by_period': {
                period: {
                    'household': 'household',
                    'person': 'person',
                    'batch_size': 3,
                    'batch_index': 0,
                    }
                },
            'config_files_directory': self.data_dir
            }
        # TODO: Add batch_size
        survey_scenario.init_from_data(data = data)

        simulation = survey_scenario.simulations["baseline"]
        result = simulation.calculate('rent', period)
        assert len(result) == 4
        assert (result == input_data_frame_by_entity['rent']).all()

if __name__ == "__main__":
    # openfisca_survey_manager_location = Path(__file__).parent.parent
    # os.environ["CI"] = "True"
    print(openfisca_survey_manager_location)
    print(f"Default config files directory: {default_config_files_directory}")
    test = TestParquet()
    test.test_build_collection()
    test.test_load_parquet()