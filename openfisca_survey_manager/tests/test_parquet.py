"""
Test the ability to store parquet files in collections, without converting them to HDF5.
"""

import os
import pytest
import pandas as pd
import logging
from unittest import TestCase

from openfisca_core import periods
from openfisca_survey_manager import openfisca_survey_manager_location, default_config_files_directory
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.scripts.build_collection import add_survey_to_collection
from openfisca_survey_manager.scripts.build_collection import build_survey_collection
from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario
from openfisca_survey_manager.tests import tax_benefit_system
from openfisca_survey_manager.surveys import NoMoreDataError

logger = logging.getLogger(__name__)


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

    def test_load_parquet_monolithic(self):
        """
        Test the loading all the data from parquet files in memory.
        """
        # Create survey scenario
        survey_scenario = AbstractSurveyScenario()
        survey_name = 'test_parquet_collection_2020'
        survey_collection = SurveyCollection.load(
            config_files_directory=self.data_dir,
            collection=self.collection_name,
            )
        survey = survey_collection.get_survey(survey_name)
        table = survey.get_values(
            table="household", ignorecase=True
            )
        input_data_frame_by_entity = table
        survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
        survey_scenario.period = 2020
        survey_scenario.used_as_input_variables = ["rent"]
        survey_scenario.collection = self.collection_name
        period = periods.period('2020-01')
        results = {
            'rent': [],
            'housing_tax': [],
            'income_tax': [],
            }
        data = {
            'collection': 'test_parquet_collection',
            'survey': 'test_parquet_collection_2020',
            'input_data_table_by_entity_by_period': {
                period: {
                    'household': 'household',
                    'person': 'person',
                    }
                },
            'config_files_directory': self.data_dir
            }
        survey_scenario.init_from_data(data = data)

        simulation = survey_scenario.simulations["baseline"]
        sim_res = simulation.calculate('housing_tax', period.this_year).flatten().tolist()
        results['housing_tax'] += sim_res
        sim_res = simulation.calculate('rent', period).flatten().tolist()
        results['rent'] += sim_res
        sim_res = simulation.calculate('income_tax', period).flatten().tolist()
        results['income_tax'] += sim_res

        logger.debug(f"{results=}")
        assert len(results['rent']) == 4
        assert (results['rent'] == input_data_frame_by_entity['rent']).all()
        assert (results['housing_tax'] == [500.0, 1000.0, 1500.0, 2000.0])
        assert (results['income_tax'] == [195.00001525878906, 3.0, 510.0000305175781, 600.0, 750.0])

    def test_load_parquet_batch(self):
        """
        Test the batch loading of data from parquet files. This allow loading larger than memory datasets.
        """
        df = pd.read_parquet(
            os.path.join(self.data_dir, self.collection_name, "household.parquet")
            )
        assert len(df) == 4
        assert (df.columns == ["household_id", "rent", "household_weight", "accommodation_size"]).all()
        assert df.rent.sum() == 10300

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
        assert (table.columns == ["household_id", "rent", "household_weight", "accommodation_size"]).all()
        assert table.rent.sum() == 10300

        # Create survey scenario
        survey_scenario = AbstractSurveyScenario()
        input_data_frame_by_entity = table
        survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
        survey_scenario.period = 2020
        survey_scenario.used_as_input_variables = ["rent"]
        survey_scenario.collection = self.collection_name
        period = periods.period('2020-01')
        results = {
            'rent': [],
            'housing_tax': [],
            'income_tax': [],
            }
        batch_size = 2
        batch_index = 0
        while True:
            try:
                data = {
                    'collection': 'test_parquet_collection',
                    'survey': 'test_parquet_collection_2020',
                    'input_data_table_by_entity_by_period': {
                        period: {
                            'household': 'household',
                            'person': 'person',
                            'batch_size': batch_size,
                            'batch_index': batch_index,
                            }
                        },
                    'config_files_directory': self.data_dir
                    }
                survey_scenario.init_from_data(data = data)

                simulation = survey_scenario.simulations["baseline"]
                sim_res = simulation.calculate('housing_tax', period.this_year).flatten().tolist()
                results['housing_tax'] += sim_res
                sim_res = simulation.calculate('rent', period).flatten().tolist()
                results['rent'] += sim_res
                sim_res = simulation.calculate('income_tax', period).flatten().tolist()
                results['income_tax'] += sim_res
                logger.debug("XXXXXXXXXXXXXXXXXXXXXx Next batch XXXXXXXXXXXXXXXXXXXXXx")
                batch_index += 1
            except NoMoreDataError:
                logger.debug("No more data")
                break
        logger.debug(f"{results=}")
        assert len(results['rent']) == 4
        assert (results['rent'] == input_data_frame_by_entity['rent']).all()
        assert (results['housing_tax'] == [500.0, 1000.0, 1500.0, 2000.0])
        assert (results['income_tax'] == [195.00001525878906, 3.0, 510.0000305175781, 600.0, 750.0])


if __name__ == "__main__":
    # openfisca_survey_manager_location = Path(__file__).parent.parent
    # os.environ["CI"] = "True"
    logger.debug(openfisca_survey_manager_location)
    logger.debug(f"Default config files directory: {default_config_files_directory}")
    test = TestParquet()
    test.test_build_collection()
    test.test_load_parquet()
    logger.debug("Done")
