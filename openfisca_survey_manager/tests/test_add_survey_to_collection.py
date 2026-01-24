import pandas as pd
import pytest

from openfisca_survey_manager.input_dataframe_generator import set_table_in_survey
from openfisca_survey_manager.scripts.build_collection import (
    add_survey_to_collection,
)
from openfisca_survey_manager.survey_collections import SurveyCollection


@pytest.mark.order(after="test_write_parquet.py::test_write_parquet_one_file_per_entity")
def test_add_survey_to_collection_parquet(parquet_data):
    name = "fake"
    survey_name = "test_parquet"
    data_dir = parquet_data
    survey_collection = SurveyCollection(name=name, config_files_directory=str(data_dir))
    saved_fake_survey_file_path = data_dir / "test_parquet_collection" / "household.parquet"
    add_survey_to_collection(
        survey_name=survey_name,
        survey_collection=survey_collection,
        parquet_files=[str(saved_fake_survey_file_path)],
    )
    ordered_dict = survey_collection.to_json()
    assert survey_name in list(ordered_dict["surveys"].keys())


@pytest.mark.order(after="test_write_parquet.py::test_write_parquet_one_file_per_entity")
def test_set_table_in_survey_parquet(parquet_data):
    data_dir = parquet_data
    filepath = data_dir / "test_parquet_collection" / "household.parquet"
    input_dataframe = pd.read_parquet(filepath)
    survey_name = "test_parquet"
    collection = "test_parquet_collection"

    set_table_in_survey(
        input_dataframe,
        entity="foyer",
        period=2020,
        survey_name=survey_name,
        collection=collection,
        config_files_directory=str(data_dir),
    )
    survey_collection = SurveyCollection.load(collection=collection, config_files_directory=str(data_dir))
    survey = survey_collection.get_survey(survey_name)
    assert survey is not None
