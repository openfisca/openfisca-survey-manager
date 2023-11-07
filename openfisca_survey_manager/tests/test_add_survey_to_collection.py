import os
import pandas as pd
import pytest


from openfisca_survey_manager import openfisca_survey_manager_location
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.scripts.build_collection import add_survey_to_collection
from openfisca_survey_manager.input_dataframe_generator import set_table_in_survey


def test_add_survey_to_collection():
    name = 'fake'
    survey_name = 'fake_survey'
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )
    survey_collection = SurveyCollection(name = name)
    saved_fake_survey_file_path = os.path.join(data_dir, 'help.sas7bdat')
    add_survey_to_collection(
        survey_name = survey_name,
        survey_collection = survey_collection,
        sas_files = [saved_fake_survey_file_path],
        stata_files = []
        )
    ordered_dict = survey_collection.to_json()
    assert survey_name in list(ordered_dict['surveys'].keys())


@pytest.mark.order(after="test_surveys.py::test_survey")
def test_set_table_in_survey_first_year():
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager/tests/data_files',
        )
    input_dataframe = pd.DataFrame({"rfr": [1_000, 2_000, 100_000]})
    survey_name = 'test_set_table_in_survey_2020'
    collection = "fake"
    set_table_in_survey(input_dataframe, entity="foyer", period="2020", collection = collection, survey_name = survey_name, config_files_directory=data_dir)

    # Read survey
    survey_collection = SurveyCollection.load(config_files_directory = data_dir, collection=collection)
    survey = survey_collection.get_survey(survey_name)
    table = survey.get_values(
        table="foyer_2020", ignorecase=True
        )
    assert len(table) == 3
    assert table.columns == ["rfr"]
    assert table.rfr.sum() == 103000


@pytest.mark.order(after="test_set_table_in_survey_first_year")
def test_set_table_in_survey_second_year():
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager/tests/data_files',
        )
    input_dataframe = pd.DataFrame({"rfr": [1_021, 2_021, 100_021]})
    survey_name = 'test_set_table_in_survey_2021'
    collection = "fake"
    set_table_in_survey(input_dataframe, entity="foyer", period="2021", collection = collection, survey_name = survey_name, config_files_directory=data_dir)

    # Read first survey
    survey_name = 'test_set_table_in_survey_2020'
    survey_collection = SurveyCollection.load(config_files_directory = data_dir, collection=collection)
    survey = survey_collection.get_survey(survey_name)
    table = survey.get_values(
        table="foyer_2020", ignorecase=True
        )
    assert len(table) == 3
    assert table.columns == ["rfr"]
    assert table.rfr.sum() == 103000

    # Read second survey
    survey_name = 'test_set_table_in_survey_2021'
    survey_collection = SurveyCollection.load(config_files_directory = data_dir, collection=collection)
    survey = survey_collection.get_survey(survey_name)
    table = survey.get_values(
        table="foyer_2021", ignorecase=True
        )
    assert len(table) == 3
    assert table.columns == ["rfr"]
    assert table.rfr.sum() == 103063
