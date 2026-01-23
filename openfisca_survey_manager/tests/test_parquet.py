import logging
import pandas as pd
import pytest
from pathlib import Path
from openfisca_core import periods

from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario
from openfisca_survey_manager.scripts.build_collection import (
    add_survey_to_collection,
    build_survey_collection,
)
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import NoMoreDataError
from openfisca_survey_manager.tests import tax_benefit_system

logger = logging.getLogger(__name__)


def test_add_survey_to_collection_parquet(parquet_data):
    """Test adding a parquet survey to a collection."""
    collection_name = "test_parquet_collection"
    survey_name = "test_parquet_survey"
    survey_collection = SurveyCollection(name=collection_name, config_files_directory=str(parquet_data))
    survey_file_path = parquet_data / collection_name
    add_survey_to_collection(
        survey_name=survey_name,
        survey_collection=survey_collection,
        parquet_files=[str(survey_file_path)],
    )
    ordered_dict = survey_collection.to_json()
    assert survey_name in list(ordered_dict["surveys"].keys())


def test_build_collection(parquet_data):
    """Test building a survey collection from parquet files."""
    collection_name = "test_parquet_collection"
    data_directory_path_by_survey_suffix = {
        "2020": str(parquet_data / collection_name),
    }
    build_survey_collection(
        collection_name=collection_name,
        data_directory_path_by_survey_suffix=data_directory_path_by_survey_suffix,
        replace_metadata=False,
        replace_data=False,
        source_format="parquet",
        config_files_directory=str(parquet_data),
    )


def test_load_single_parquet_monolithic(parquet_data):
    """Test loading all the data from parquet files in memory."""
    collection_name = "test_parquet_collection"
    survey_name = f"{collection_name}_2020"

    data_directory_path_by_survey_suffix = {
        "2020": str(parquet_data / collection_name),
    }
    build_survey_collection(
        collection_name=collection_name,
        data_directory_path_by_survey_suffix=data_directory_path_by_survey_suffix,
        replace_metadata=True,
        replace_data=True,
        source_format="parquet",
        config_files_directory=str(parquet_data),
    )

    survey_scenario = AbstractSurveyScenario()
    survey_collection = SurveyCollection.load(
        config_files_directory=str(parquet_data),
        collection=collection_name,
    )
    survey = survey_collection.get_survey(survey_name)
    table = survey.get_values(table="household", ignorecase=True)
    input_data_frame_by_entity = table

    survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    survey_scenario.period = 2020
    survey_scenario.used_as_input_variables = ["rent"]
    survey_scenario.collection = collection_name
    period = periods.period("2020-01")

    data = {
        "collection": collection_name,
        "survey": survey_name,
        "input_data_table_by_entity_by_period": {
            period: {
                "household": "household",
                "person": "person",
            }
        },
        "config_files_directory": str(parquet_data),
    }
    survey_scenario.init_from_data(data=data)

    simulation = survey_scenario.simulations["baseline"]
    sim_res = simulation.calculate("housing_tax", period.this_year).flatten().tolist()
    assert len(sim_res) == 4
    assert sim_res == [500.0, 1000.0, 1500.0, 2000.0]

    rent_res = simulation.calculate("rent", period).flatten().tolist()
    assert (rent_res == input_data_frame_by_entity["rent"]).all()

    income_tax_res = simulation.calculate("income_tax", period).flatten().tolist()
    assert income_tax_res == pytest.approx([195.00001525878906, 3.0, 510.0000305175781, 600.0, 750.0])


def test_load_multiple_parquet_monolithic(parquet_data):
    """Test loading all data from parquet files in memory."""
    collection_name = "test_multiple_parquet_collection"
    data_dir = parquet_data / collection_name
    survey_scenario = AbstractSurveyScenario()
    survey_name = collection_name + "_2020"

    data_directory_path_by_survey_suffix = {
        "2020": str(data_dir),
    }
    build_survey_collection(
        collection_name=collection_name,
        data_directory_path_by_survey_suffix=data_directory_path_by_survey_suffix,
        replace_metadata=True,
        replace_data=True,
        source_format="parquet",
        config_files_directory=str(parquet_data),
        keep_original_parquet_file=True,
    )

    survey_collection = SurveyCollection.load(
        config_files_directory=str(parquet_data),
        collection=collection_name,
    )
    survey = survey_collection.get_survey(survey_name)
    table = survey.get_values(table="household", ignorecase=True)
    input_data_frame_by_entity = table

    survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    survey_scenario.period = 2020
    survey_scenario.used_as_input_variables = ["rent"]
    survey_scenario.collection = collection_name
    period = periods.period("2020-01")

    data = {
        "collection": collection_name,
        "survey": survey_name,
        "input_data_table_by_entity_by_period": {
            period: {
                "household": "household",
                "person": "person",
            }
        },
        "config_files_directory": str(parquet_data),
    }
    survey_scenario.init_from_data(data=data)

    simulation = survey_scenario.simulations["baseline"]
    sim_res = simulation.calculate("housing_tax", period.this_year).flatten().tolist()
    assert len(sim_res) == 4
    assert sim_res == [500.0, 1000.0, 1500.0, 2000.0]

    rent_res = simulation.calculate("rent", period).flatten().tolist()
    assert (rent_res == input_data_frame_by_entity["rent"]).all()

    income_tax_res = simulation.calculate("income_tax", period).flatten().tolist()
    assert income_tax_res == pytest.approx([195.00001525878906, 3.0, 510.0000305175781, 600.0, 750.0])


def test_load_parquet_batch(parquet_data):
    """Test the batch loading of data from parquet files."""
    collection_name = "test_multiple_parquet_collection"
    df = pd.read_parquet(parquet_data / collection_name / "household" / "household-0.parquet")
    df1 = pd.read_parquet(parquet_data / collection_name / "household" / "household-1.parquet")
    total_rent = df.rent.sum() + df1.rent.sum()

    # Build multi-collection
    data_directory_path_by_survey_suffix = {
        "2020": str(parquet_data / collection_name),
    }
    build_survey_collection(
        collection_name=collection_name,
        data_directory_path_by_survey_suffix=data_directory_path_by_survey_suffix,
        replace_metadata=True,
        replace_data=True,
        source_format="parquet",
        config_files_directory=str(parquet_data),
        keep_original_parquet_file=True,
    )

    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    survey_scenario.period = 2020
    survey_scenario.used_as_input_variables = ["rent"]
    survey_scenario.collection = collection_name
    period = periods.period("2020-01")

    results = {
        "rent": [],
        "housing_tax": [],
        "income_tax": [],
    }
    batch_size = 2
    batch_index = 0
    while True:
        try:
            data = {
                "collection": collection_name,
                "survey": f"{collection_name}_2020",
                "input_data_table_by_entity_by_period": {
                    period: {
                        "household": "household",
                        "person": "person",
                        "batch_size": batch_size,
                        "batch_index": batch_index,
                        "batch_entity": "household",
                        "batch_entity_key": "household_id",
                        "filtered_entity": "person",
                        "filtered_entity_on_key": "household_id",
                    }
                },
                "config_files_directory": str(parquet_data),
            }
            survey_scenario.init_from_data(data=data)

            simulation = survey_scenario.simulations["baseline"]
            results["housing_tax"] += simulation.calculate("housing_tax", period.this_year).flatten().tolist()
            results["rent"] += simulation.calculate("rent", period).flatten().tolist()
            results["income_tax"] += simulation.calculate("income_tax", period).flatten().tolist()
            batch_index += 1
        except NoMoreDataError:
            break

    assert len(results["rent"]) == 4
    assert sum(results["rent"]) == total_rent
    assert sum(results["housing_tax"]) == sum([500.0, 1000.0, 1500.0, 2000.0])
    assert sum(results["income_tax"]) == pytest.approx(sum([195.00001525878906, 3.0, 510.0000305175781, 600.0, 750.0]))
