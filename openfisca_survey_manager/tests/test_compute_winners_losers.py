import pytest
from openfisca_country_template.reforms.modify_social_security_taxation import modify_social_security_taxation
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
from openfisca_survey_manager.simulations import SecretViolationError


def test_compute_winners_losers_basics():
    survey_scenario = create_randomly_initialized_survey_scenario()
    del survey_scenario.weight_variable_by_entity
    survey_scenario.set_weight_variable_by_entity()
    period = survey_scenario.period
    variable = "pension"

    simulation = survey_scenario.simulations["baseline"]
    baseline_simulation = survey_scenario.simulations["baseline"]

    simulation.adaptative_calculate_variable(variable, period = period)
    absolute_minimal_detected_variation = 1
    relative_minimal_detected_variation = .05
    observations_threshold = 1

    winners_losers = simulation.compute_winners_losers(
        baseline_simulation,
        variable,
        period = period,
        absolute_minimal_detected_variation = absolute_minimal_detected_variation,
        relative_minimal_detected_variation = relative_minimal_detected_variation,
        observations_threshold = observations_threshold,
        )
    assert winners_losers == {
        'total': 10.0,
        'non_zero_before': 0.0,
        'non_zero_after': 0.0,
        'above_after': 0.0,
        'lower_after': 0.0,
        'neutral': 10.0,
        'tolerance_factor_used': 0.05,
        'weight_factor': 1
        }


def test_compute_winners_losers():
    survey_scenario = create_randomly_initialized_survey_scenario(reform = modify_social_security_taxation)
    del survey_scenario.weight_variable_by_entity
    survey_scenario.set_weight_variable_by_entity()
    period = survey_scenario.period
    variable = "social_security_contribution"

    simulation = survey_scenario.simulations["reform"]
    baseline_simulation = survey_scenario.simulations["baseline"]

    absolute_minimal_detected_variation = .9
    relative_minimal_detected_variation = .05
    observations_threshold = 1

    winners_losers = simulation.compute_winners_losers(
        baseline_simulation,
        variable,
        period = period,
        absolute_minimal_detected_variation = absolute_minimal_detected_variation,
        relative_minimal_detected_variation = relative_minimal_detected_variation,
        observations_threshold = observations_threshold,
        )

    winners_losers_scenario = survey_scenario.compute_winners_losers(
        variable,
        period = period,
        absolute_minimal_detected_variation = absolute_minimal_detected_variation,
        relative_minimal_detected_variation = relative_minimal_detected_variation,
        observations_threshold = observations_threshold,
        )

    assert winners_losers == {
        'total': 10.0,
        'non_zero_before': 10.0,
        'non_zero_after': 9.0,
        'above_after': 9.0,
        'lower_after': 1.0,
        'neutral': 0.0,
        'tolerance_factor_used': 0.05,
        'weight_factor': 1,
        }
    assert winners_losers == winners_losers_scenario

    observations_threshold = 10

    with pytest.raises(SecretViolationError):
        winners_losers = simulation.compute_winners_losers(
            baseline_simulation,
            variable,
            period = period,
            absolute_minimal_detected_variation = absolute_minimal_detected_variation,
            relative_minimal_detected_variation = relative_minimal_detected_variation,
            observations_threshold = observations_threshold,
            )


def test_compute_winners_losers_with_new_attributes():
    survey_scenario = create_randomly_initialized_survey_scenario(reform = modify_social_security_taxation)
    survey_scenario.absolute_minimal_detected_variation = 100
    survey_scenario.relative_minimal_detected_variation = 0.1
    survey_scenario.observations_threshold = 2

    del survey_scenario.weight_variable_by_entity
    survey_scenario.set_weight_variable_by_entity()
    period = survey_scenario.period
    variable = "social_security_contribution"

    winners_losers_scenario = survey_scenario.compute_winners_losers(
        variable,
        period = period,
        )

    assert winners_losers_scenario == {
        'total': 10.0,
        'non_zero_before': 10.0,
        'non_zero_after': 0.0,
        'above_after': 0.0,
        'lower_after': 0.0,
        'neutral': 10.0,
        'tolerance_factor_used': 0.1,
        'weight_factor': 1,
        }
