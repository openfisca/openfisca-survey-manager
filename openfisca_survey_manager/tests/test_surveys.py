
import os
import pkg_resources


from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey


def test_survey():
    name = 'fake'
    data_dir = os.path.join(
        pkg_resources.get_distribution('openfisca-survey-manager').location,
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
    survey.fill_hdf(source_format = 'sas')


if __name__ == '__main__':
    test_survey()
