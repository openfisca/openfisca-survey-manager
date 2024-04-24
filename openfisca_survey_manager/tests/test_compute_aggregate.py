from openfisca_country_template.reforms.modify_social_security_taxation import modify_social_security_taxation
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario


def test_compute_aggregate():
    survey_scenario = create_randomly_initialized_survey_scenario(reform = modify_social_security_taxation)
    period = "2017-01"
    variable = "social_security_contribution"

    aggregate_after = survey_scenario.compute_aggregate(variable, period = period)
    aggregate_before = survey_scenario.compute_aggregate(variable, period = period, use_baseline = True)

    assert aggregate_after > aggregate_before

    survey_scenario.calculate_variable("social_security_contribution", period = period)
    survey_scenario.calculate_variable("salary", period = period, use_baseline = True)

    assert 0 == survey_scenario.compute_aggregate(
        "social_security_contribution",
        period = period,
        filter_by = "salary < 3000",
        )

    assert 34489 == survey_scenario.compute_aggregate(
        "social_security_contribution",
        period = period,
        filter_by = "3000 < salary < 10000",
        ).astype(int)

    del survey_scenario.weight_variable_by_entity
    survey_scenario.set_weight_variable_by_entity()
    assert 576 == survey_scenario.compute_aggregate(
        "social_security_contribution",
        period = period,
        filter_by = "3000 < salary < 10000",
        weighted = False,
        ).astype(int)
