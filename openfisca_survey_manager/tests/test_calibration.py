
from openfisca_core.tools import assert_near
from openfisca_core import periods

from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
from openfisca_survey_manager.tests.test_scenario import generate_input_input_dataframe_by_entity
from openfisca_survey_manager.calibration import Calibration

from openfisca_survey_manager import default_config_files_directory
from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario
from openfisca_survey_manager.tests import tax_benefit_system


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

    survey_scenario.calibrate(
        period,
        target_margins_by_variable = {
            'rent': target_rent_aggregate,
            'salary': target_salary_aggregate
            },
        parameters = {"method": "raking ratio", "id_variable": "household_id", "id_variable_link": "household_id_ind"},
        other_entity_count = 700,
        target_entity_count = 300,
        )
    assert_near(survey_scenario.compute_aggregate("rent", period = period), target_rent_aggregate, relative_error_margin = 0.1)
    assert_near(survey_scenario.compute_aggregate("salary", period = period), target_salary_aggregate, relative_error_margin = 0.1)
    dataframe_by_entity = survey_scenario.create_data_frame_by_entity(["household_weight", "person_weight"], merge = False)
    assert_near(sum(dataframe_by_entity["household"]["household_weight"]), 300, relative_error_margin = 0.1)
    assert_near(sum(dataframe_by_entity["person"]["person_weight"]), 700, relative_error_margin = 0.1)


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


def test_simulation_calibration_variable_entity_is_weight_entity_with_hyperbolic_sinus():
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
        parameters = {"method": "hyperbolic sinus", 'alpha': 1.2},
        )

    calibration.calibrate(inplace = True)
    assert all(calibration.weight != calibration.initial_weight)

    assert_near(simulation.compute_aggregate("rent", period = period), target_rent_aggregate)

    # See if propagation to derived weights is done well
    person_weight_after = simulation.calculate("person_weight", period)
    assert all(person_weight_after != person_weight_before)
    assert calibration.initial_entity_count != calibration.target_entity_count
    assert simulation.calculate("household_weight", period).sum() == calibration.target_entity_count


def test_simulation_calibration_input_from_data():
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        10, 5, 5000, 1000)
    survey_scenario = AbstractSurveyScenario()
    weight_variable_by_entity = {
        "person": "person_weight",
        "household": "household_weight",
        }
    survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
    survey_scenario.period = '2017-01'
    survey_scenario.used_as_input_variables = ['salary', 'rent', 'household_weight']
    period = periods.period('2017-01')
    target_rent_aggregate = 200000

    data = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            },
        'config_files_directory': default_config_files_directory
        }
    calibration_kwargs = {'target_margins_by_variable': {'rent': target_rent_aggregate}, 'target_entity_count': 300, 'parameters': {'method': 'logit', 'up': 4, 'invlo': 4}}
    survey_scenario.set_weight_variable_by_entity(weight_variable_by_entity)
    assert survey_scenario.weight_variable_by_entity == weight_variable_by_entity
    survey_scenario.init_from_data(data = data, calibration_kwargs=calibration_kwargs)
    for simulation_name, simulation in survey_scenario.simulations.items():
        assert simulation.weight_variable_by_entity == weight_variable_by_entity, f"{simulation_name} weight_variable_by_entity does not match {weight_variable_by_entity}"
        assert (survey_scenario.calculate_series("household_weight", period, simulation = simulation_name) != 0).all()
    return survey_scenario
