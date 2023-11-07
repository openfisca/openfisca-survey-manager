from openfisca_country_template.reforms.modify_social_security_taxation import modify_social_security_taxation
from openfisca_survey_manager.aggregates import AbstractAggregates
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario


def test_aggregates():

    survey_scenario = create_randomly_initialized_survey_scenario(reform = modify_social_security_taxation)
    period = "2017-01"

    variables = [
        "social_security_contribution",
        "salary",
        ]
    aggregates = AbstractAggregates(survey_scenario=survey_scenario)
    aggregates.amount_unit = 1.0
    aggregates.beneficiaries_unit = 1.0
    aggregates.aggregate_variables = variables

    df = aggregates.compute_aggregates(reform = True, actual = False)

    for variable in variables:
        aggregate_before = survey_scenario.compute_aggregate(variable, period = period, use_baseline = True)
        aggregate_after = survey_scenario.compute_aggregate(variable, period = period)
        assert df.loc[variable, "baseline_amount"] == int(aggregate_before)
        assert df.loc[variable, "reform_amount"] == int(aggregate_after)
