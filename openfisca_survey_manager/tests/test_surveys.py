import pandas as pd
import pytest

from openfisca_survey_manager.input_dataframe_generator import set_table_in_survey
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey


@pytest.fixture
def test_data(tmp_path):
    """Fixture to provide a clean test data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create a basic config.ini
    config_file = data_dir / "config.ini"
    config_file.write_text(f"""
[collections]
collections_directory = {data_dir}
fake = {data_dir}/fake.json

[data]
output_directory = {data_dir}
tmp_directory = {data_dir}/tmp
""")
    (data_dir / "tmp").mkdir()

    # Create empty fake.json
    json_file = data_dir / "fake.json"
    json_file.write_text('{"name": "fake", "surveys": {}}')

    return data_dir


def test_survey_parquet(test_data):
    name = "fake"
    data_dir = test_data

    survey_collection = SurveyCollection(
        name=name, config_files_directory=str(data_dir), json_file_path=str(data_dir / "fake.json")
    )

    saved_fake_survey_hdf5_file_path = data_dir / "fake.hdf5"
    # Create dummy parquet
    saved_fake_survey_file_path = data_dir / "test.parquet"
    pd.DataFrame({"a": [1]}).to_parquet(saved_fake_survey_file_path)

    survey = Survey(
        hdf5_file_path=str(saved_fake_survey_hdf5_file_path),
        name="fake_survey",
        sas_files=[str(saved_fake_survey_file_path)],
        survey_collection=survey_collection,
    )
    survey.insert_table(name="test_parquet")
    survey.fill_store(source_format="parquet")


def test_survey_load(test_data):
    survey_name = "test_set_table_in_survey_2021"
    collection = "fake"
    data_dir = test_data

    # First, create the survey data
    input_df = pd.DataFrame({"foyer_id": [1], "salary": [1000]})
    set_table_in_survey(
        input_df,
        entity="foyer",
        period=2021,
        collection=collection,
        survey_name=survey_name,
        config_files_directory=str(data_dir),
    )

    # Now load it back
    survey_collection = SurveyCollection.load(collection=collection, config_files_directory=str(data_dir))
    survey = survey_collection.get_survey(survey_name)
    assert "foyer_2021" in survey.tables
