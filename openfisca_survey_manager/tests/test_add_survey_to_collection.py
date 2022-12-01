

import os
import pkg_resources


from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.scripts.build_collection import add_survey_to_collection

# Travis, Gitlab runner, Gihub Action and circle has env variable "CI" set by default
if 'CI' in os.environ:
    is_in_ci = True
else:
    is_in_ci = False


def test_add_survey_to_collection():
    if is_in_ci:
        return
    name = 'fake'
    survey_name = 'fake_survey'
    data_dir = os.path.join(
        pkg_resources.get_distribution('openfisca-survey-manager').location,
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
