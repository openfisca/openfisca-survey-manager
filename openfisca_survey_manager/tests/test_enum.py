import pandas as pd
from openfisca_country_template.variables.housing import HousingOccupancyStatus
from openfisca_survey_manager.tests import tax_benefit_system

from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario


def test_generation():
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
    survey_scenario.period = "2025-06"
    survey_scenario.used_as_input_variables = ['housing_occupancy_status']

    statuses = [HousingOccupancyStatus.free_lodger, HousingOccupancyStatus.tenant]
    data = {
        "input_data_frame": pd.DataFrame({
            "housing_occupancy_status": pd.Series([v.name for v in statuses]),
            "household_id": [0, 1],
            "household_role_index": [0, 0]
            })
        }
    survey_scenario.init_from_data(data=data)
    result = survey_scenario.calculate_variable("housing_occupancy_status", survey_scenario.period)
    assert ((result == pd.Series([v.index for v in statuses])).all())
