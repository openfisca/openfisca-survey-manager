from openfisca_country_template.reforms.modify_social_security_taxation import modify_social_security_taxation
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario


def test_compute_winners_loosers():
    survey_scenario = create_randomly_initialized_survey_scenario(reform = modify_social_security_taxation)
    period = survey_scenario.year
    variable = "social_security_contribution"

    aggregate_after = survey_scenario.compute_aggregate(variable, period = period)
    aggregate_before = survey_scenario.compute_aggregate(variable, period = period, use_baseline = True)

    assert aggregate_after > aggregate_before

    simulation = survey_scenario.simulation
    baseline_simulation = survey_scenario.baseline_simulation

    absolute_minimal_detected_variation = .9
    relative_minimal_detected_variation = .05
    observations_thershold = 1

    below, neutral, above = simulation.compute_winners_loosers(
        baseline_simulation,
        variable,
        period = period,
        absolute_minimal_detected_variation = absolute_minimal_detected_variation,
        relative_minimal_detected_variation = relative_minimal_detected_variation,
        observations_thershold = observations_thershold,
        )

    below_scenario, neutral_scenario, above_scenario = survey_scenario.compute_winners_loosers(
        variable,
        period = period,
        absolute_minimal_detected_variation = absolute_minimal_detected_variation,
        relative_minimal_detected_variation = relative_minimal_detected_variation,
        observations_thershold = observations_thershold,
        )

    assert (below, neutral, above) == (1, 0, 9)
    assert (below, neutral, above) == (below_scenario, neutral_scenario, above_scenario)
