import pytest


from openfisca_core.tools import assert_near


from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
from openfisca_survey_manager.calibration import Calibration


def test_calibration_variable_entity_is_weight_entity():
    survey_scenario = create_randomly_initialized_survey_scenario(collection=None)
    period = "2017-01"
    survey_scenario.period = period
    person_weight_before = survey_scenario.calculate_series("person_weight", period)
    # 'initial_rent_aggregate' is assigned to but never used initial_rent_aggregate = survey_scenario.compute_aggregate("rent", period = period)
    target_rent_aggregate = 200000

    survey_scenario.calibrate(
        period,
        target_margins_by_variable = {
            'rent': target_rent_aggregate,
            },
        parameters = {"method": "raking ratio"},
        )

    for _, simulation in survey_scenario.simulations.items():
        assert all(simulation.calibration.weight != simulation.calibration.initial_weight)

    assert_near(survey_scenario.compute_aggregate("rent", period = period), target_rent_aggregate)

    # See if propagation to derived weights is done well
    person_weight_after = survey_scenario.calculate_series("person_weight", period)
    assert (person_weight_after != person_weight_before).all()


def test_calibration_variable_entity_is_not_weight_entity():
    survey_scenario = create_randomly_initialized_survey_scenario(collection=None)
    period = "2017-01"
    survey_scenario.period = period
    target_rent_aggregate = 200000
    target_salary_aggregate = 1e7

    with pytest.raises(NotImplementedError):
        survey_scenario.calibrate(
            period,
            target_margins_by_variable = {
                'rent': target_rent_aggregate,
                'salary': target_salary_aggregate
                },
            parameters = {"method": "raking ratio"},
            )


def test_simulation_calibration_variable_entity_is_weight_entity():
    survey_scenario = create_randomly_initialized_survey_scenario(collection=None)
    period = "2017-01"
    survey_scenario.period = period
    simulation = list(survey_scenario.simulations.values())[0]
    person_weight_before = simulation.calculate("person_weight", period)

    # initial_rent_aggregate = simulation.compute_aggregate("rent", period = period)
    target_rent_aggregate = 200000

    calibration = Calibration(
        simulation,
        period = "2017-01",
        target_margins = {
            'rent': target_rent_aggregate,
            },
        target_entity_count = 300,
        parameters = {"method": "raking ratio"},
        )

    calibration.calibrate(inplace = True)
    assert all(calibration.weight != calibration.initial_weight)

    assert_near(simulation.compute_aggregate("rent", period = period), target_rent_aggregate)

    # See if propagation to derived weights is done well
    person_weight_after = simulation.calculate("person_weight", period)
    assert all(person_weight_after != person_weight_before)
    assert calibration.initial_entity_count != calibration.target_entity_count
    assert simulation.calculate("household_weight", period).sum() == calibration.target_entity_count
