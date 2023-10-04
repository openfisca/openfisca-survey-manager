import multiprocessing
import os
import pytest


from openfisca_survey_manager import openfisca_survey_manager_location
from openfisca_survey_manager.survey_collections import SurveyCollection


@pytest.mark.order(after="test_add_survey_to_collection.py::test_set_table_in_survey_first_year")
def test_concurent_read_table_in_survey():

    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager/tests/data_files',
        )
    survey_name = 'test_set_table_in_survey_2020'
    collection = "fake"
    table_name = "foyer_2020"

    # collection = "leximpact"
    # survey_name = "leximpact_2021"

    # data_dir = "/media/data-nvme/dev/src/LEXIMPACT/leximpact-socio-fiscal-simu-etat/deploy/"

    def read_survey():
        survey_collection = SurveyCollection.load(config_files_directory = data_dir, collection=collection)
        survey = survey_collection.get_survey(survey_name)
        table = survey.get_values(
            table=table_name, ignorecase=True
            )
        assert len(table.columns) == 12

    # multiprocessing.set_start_method('spawn')
    multiprocessing.set_start_method('fork')
    processes = [multiprocessing.Process(target=read_survey) for _ in range(50)]
    for p in processes:
        p.start()

    for p in processes:
        p.join()
