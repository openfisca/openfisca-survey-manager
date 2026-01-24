from pathlib import Path
import shutil
import pandas as pd
import pytest

from openfisca_survey_manager.input_dataframe_generator import set_table_in_survey
from openfisca_survey_manager.paths import openfisca_survey_manager_location
from openfisca_survey_manager.scripts.build_collection import add_survey_to_collection
from openfisca_survey_manager.survey_collections import SurveyCollection


@pytest.fixture
def test_data_dir(tmp_path):
    """Fixture to provide a clean test data directory with necessary files."""
    data_dir = tmp_path / "data_files"
    data_dir.mkdir()

    # Create a basic config.ini
    config_file = data_dir / "config.ini"
    config_file.write_text(f"""
[collections]
collections_directory = {data_dir}

[data]
output_directory = {data_dir}
tmp_directory = /tmp
""")

    # Source data files from the project
    source_dir = Path(openfisca_survey_manager_location) / "openfisca_survey_manager" / "tests" / "data_files"

    # Copy some required files for tests
    required_files = ["help.sas7bdat"]
    for f in required_files:
        if (source_dir / f).exists():
            shutil.copy(source_dir / f, data_dir / f)

    # Create test.parquet if needed
    pd.DataFrame({"a": [1, 2]}).to_parquet(data_dir / "test.parquet")

    # Create test_parquet_collection/household.parquet
    coll_dir = data_dir / "test_parquet_collection"
    coll_dir.mkdir()
    pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4],
            "rent": [1100, 2200, 3000, 4000],
            "household_weight": [550, 1500, 700, 200],
            "accommodation_size": [50, 100, 150, 200],
        }
    ).to_parquet(coll_dir / "household.parquet")

    return data_dir


def test_add_survey_to_collection_parquet(test_data_dir):
    name = "fake"
    survey_name = "test_parquet"
    survey_collection = SurveyCollection(name=name, config_files_directory=str(test_data_dir))
    parquet_file = test_data_dir / "test.parquet"
    add_survey_to_collection(
        survey_name=survey_name,
        survey_collection=survey_collection,
        parquet_files=[str(parquet_file)],
    )
    ordered_dict = survey_collection.to_json()
    assert survey_name in list(ordered_dict["surveys"].keys())


def test_set_table_in_survey_parquet(test_data_dir):
    filepath = test_data_dir / "test_parquet_collection" / "household.parquet"
    input_dataframe = pd.read_parquet(filepath)
    survey_name = "test_parquet"
    collection = "fake"
    set_table_in_survey(
        input_dataframe,
        entity="foyer",
        period="2023",
        collection=collection,
        survey_name=survey_name,
        config_files_directory=str(test_data_dir),
    )

    # Read survey
    survey_collection = SurveyCollection.load(config_files_directory=str(test_data_dir), collection=collection)
    survey = survey_collection.get_survey(survey_name)
    table = survey.get_values(table="foyer_2023", ignorecase=True)
    assert len(table) == 4
    assert table.household_weight.sum() == 2950


def test_add_survey_to_collection(test_data_dir):
    name = "fake"
    survey_name = "fake_survey"
    survey_collection = SurveyCollection(name=name, config_files_directory=str(test_data_dir))
    sas_file = test_data_dir / "help.sas7bdat"
    if not sas_file.exists():
        pytest.skip("help.sas7bdat not found")

    add_survey_to_collection(
        survey_name=survey_name,
        survey_collection=survey_collection,
        sas_files=[str(sas_file)],
        stata_files=[],
    )
    ordered_dict = survey_collection.to_json()
    assert survey_name in list(ordered_dict["surveys"].keys())


def test_set_table_in_survey_first_year(test_data_dir):
    input_dataframe = pd.DataFrame({"rfr": [1_000, 2_000, 100_000]})
    survey_name = "test_set_table_in_survey_2020"
    collection = "fake"
    set_table_in_survey(
        input_dataframe,
        entity="foyer",
        period="2020",
        collection=collection,
        survey_name=survey_name,
        config_files_directory=str(test_data_dir),
    )

    # Read survey
    survey_collection = SurveyCollection.load(config_files_directory=str(test_data_dir), collection=collection)
    survey = survey_collection.get_survey(survey_name)
    table = survey.get_values(table="foyer_2020", ignorecase=True)
    assert len(table) == 3
    assert table.rfr.sum() == 103000


def test_set_table_in_survey_second_year(test_data_dir):
    # Year 1
    input_df1 = pd.DataFrame({"rfr": [1_000, 2_000, 100_000]})
    collection = "fake"
    set_table_in_survey(
        input_df1,
        entity="foyer",
        period="2020",
        collection=collection,
        survey_name="test_set_table_in_survey_2020",
        config_files_directory=str(test_data_dir),
    )

    # Year 2
    input_df2 = pd.DataFrame({"rfr": [1_021, 2_021, 100_021]})
    survey_name = "test_set_table_in_survey_2021"
    set_table_in_survey(
        input_df2,
        entity="foyer",
        period="2021",
        collection=collection,
        survey_name=survey_name,
        config_files_directory=str(test_data_dir),
    )

    # Read second survey
    survey_collection = SurveyCollection.load(config_files_directory=str(test_data_dir), collection=collection)
    survey = survey_collection.get_survey(survey_name)
    table = survey.get_values(table="foyer_2021", ignorecase=True)
    assert len(table) == 3
    assert table.rfr.sum() == 103063
