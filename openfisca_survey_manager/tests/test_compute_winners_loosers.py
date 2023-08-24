import pytest
from openfisca_country_template.reforms.modify_social_security_taxation import modify_social_security_taxation
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
from openfisca_survey_manager.simulations import SecretViolationError


def test_compute_winners_loosers():
    survey_scenario = create_randomly_initialized_survey_scenario(reform = modify_social_security_taxation)
    del survey_scenario.weight_variable_by_entity
    period = survey_scenario.year
    variable = "social_security_contribution"

    aggregate_after = survey_scenario.compute_aggregate(variable, period = period)
    aggregate_before = survey_scenario.compute_aggregate(variable, period = period, use_baseline = True)

    assert aggregate_after > aggregate_before

    simulation = survey_scenario.simulation
    baseline_simulation = survey_scenario.baseline_simulation

    absolute_minimal_detected_variation = .9
    relative_minimal_detected_variation = .05
    observations_threshold = 1

    winners_loosers = simulation.compute_winners_loosers(
        baseline_simulation,
        variable,
        period = period,
        absolute_minimal_detected_variation = absolute_minimal_detected_variation,
        relative_minimal_detected_variation = relative_minimal_detected_variation,
        observations_threshold = observations_threshold,
        )

    winners_loosers_scenario = survey_scenario.compute_winners_loosers(
        variable,
        period = period,
        absolute_minimal_detected_variation = absolute_minimal_detected_variation,
        relative_minimal_detected_variation = relative_minimal_detected_variation,
        observations_threshold = observations_threshold,
        )

    assert winners_loosers == {
        'total': 10.0,
        'non_zero_before': 10.0,
        'non_zero_after': 9.0,
        'above_after': 9.0,
        'lower_after': 1.0,
        'neutral': 0.0,
        'tolerance_factor_used': 0.05,
        'weight_factor': 1,
        }
    assert winners_loosers == winners_loosers_scenario

    observations_threshold = 10

    with pytest.raises(SecretViolationError):
        winners_loosers = simulation.compute_winners_loosers(
            baseline_simulation,
            variable,
            period = period,
            absolute_minimal_detected_variation = absolute_minimal_detected_variation,
            relative_minimal_detected_variation = relative_minimal_detected_variation,
            observations_threshold = observations_threshold,
            )
