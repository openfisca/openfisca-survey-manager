import pytest
from openfisca_country_template.reforms.modify_social_security_taxation import modify_social_security_taxation
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
from openfisca_survey_manager.simulations import SecretViolationError


def test_compute_aggregate():
    survey_scenario = create_randomly_initialized_survey_scenario(reform = modify_social_security_taxation)
    period = survey_scenario.year
    variable = "social_security_contribution"

    aggregate_after = survey_scenario.compute_aggregate(variable, period = period)
    aggregate_before = survey_scenario.compute_aggregate(variable, period = period, use_baseline = True)

    assert aggregate_after > aggregate_before

    survey_scenario.create_data_frame_by_entity(["salary", "social_security_contribution"])

    assert 0 == survey_scenario.compute_aggregate(
        "social_security_contribution",
        period = period,
        filter_by = "salary < 3000",
        )

    assert 576 == survey_scenario.compute_aggregate(
        "social_security_contribution",
        period = period,
        filter_by = "3000 < salary < 10000",
        ).astype(int)
