import os


from openfisca_survey_manager import openfisca_survey_manager_location
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey


def test_survey_parquet():
    name = 'fake'
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )

    survey_collection = SurveyCollection(
        name = name,
        config_files_directory = data_dir,
        json_file_path = os.path.join(data_dir, 'fake.json')
        )

    saved_fake_survey_hdf5_file_path = os.path.join(data_dir, 'fake.hdf5')
    saved_fake_survey_file_path = os.path.join(data_dir, 'test.parquet')
    survey = Survey(
        hdf5_file_path = saved_fake_survey_hdf5_file_path,
        name = 'fake_survey',
        sas_files = [saved_fake_survey_file_path],
        survey_collection = survey_collection,
        )
    survey.insert_table(name = 'test_parquet')
    survey.fill_store(source_format = 'parquet')


def test_survey():
    name = 'fake'
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )

    survey_collection = SurveyCollection(
        name = name,
        config_files_directory = data_dir,
        json_file_path = os.path.join(data_dir, 'fake.json')
        )

    saved_fake_survey_hdf5_file_path = os.path.join(data_dir, 'fake.hdf5')
    saved_fake_survey_file_path = os.path.join(data_dir, 'help.sas7bdat')
    survey = Survey(
        hdf5_file_path = saved_fake_survey_hdf5_file_path,
        name = 'fake_survey',
        sas_files = [saved_fake_survey_file_path],
        survey_collection = survey_collection,
        )
    survey.insert_table(name = 'help')
    survey.fill_store(source_format = 'sas')


def test_survey_load():
    survey_name = 'test_set_table_in_survey_2021'
    collection = 'fake'
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )
    survey_collection = SurveyCollection.load(
        collection=collection, config_files_directory=data_dir
        )
    survey = survey_collection.get_survey(survey_name)
    for table_name, _ in survey.tables.items():
        assert table_name == "foyer_2021"


if __name__ == '__main__':
    test_survey()
