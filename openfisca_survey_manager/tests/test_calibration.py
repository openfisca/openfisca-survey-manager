import pytest


from openfisca_core.tools import assert_near

# from openfisca_survey_manager.input_dataframe_generator import (
#     make_input_dataframe_by_entity,
#     random_data_generator,
#     randomly_init_variable,
#     )
# from openfisca_survey_manager.scenarios import AbstractSurveyScenario
# from openfisca_survey_manager.tests import tax_benefit_system
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario

from openfisca_survey_manager.calibration import Calibration


def test_calibration_variable_entity_is_weight_entity():
    survey_scenario = create_randomly_initialized_survey_scenario(collection=None)
    period = "2017-01"
    survey_scenario.period = period
    person_weight_before = survey_scenario.calculate_series("person_weight", period)

    calibration = Calibration(survey_scenario, weight_variable_name = "household_weight")
    # 'initial_rent_aggregate' is assigned to but never used initial_rent_aggregate = survey_scenario.compute_aggregate("rent", period = period)
    target_rent_aggregate = 200000

    calibration.set_target_margin('rent', target_rent_aggregate)
    calibration.set_parameters("method", "raking ratio")
    calibration.calibrate()
    assert all(calibration.weight != calibration.initial_weight)
    calibration.set_calibrated_weights()

    assert_near(survey_scenario.compute_aggregate("rent", period = period), target_rent_aggregate)

    # See if propagation to derived weights is done well
    person_weight_after = survey_scenario.calculate_series("person_weight", period)
    assert (person_weight_after != person_weight_before).all()


def test_calibration_variable_entity_is_not_weight_entity():
    survey_scenario = create_randomly_initialized_survey_scenario(collection=None)
    period = "2017-01"
    survey_scenario.period = period
    # is assigned to but never used person_weight_before = survey_scenario.calculate_series("person_weight", period)

    calibration = Calibration(survey_scenario, weight_variable_name = "household_weight")
    # is assigned to but never used initial_salary_aggregate = survey_scenario.compute_aggregate("salary", period = period)
    target_salary_aggregate = 1e7

    calibration.set_target_margin('salary', target_salary_aggregate)
    calibration.set_parameters("method", "raking ratio")

    with pytest.raises(NotImplementedError):
        calibration.calibrate()
