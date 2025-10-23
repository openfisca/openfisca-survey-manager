import pytest
from openfisca_country_template.reforms.modify_social_security_taxation import modify_social_security_taxation

from openfisca_survey_manager.aggregates import AbstractAggregates
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario


@pytest.fixture
def aggregates_test_setup():
    survey_scenario = create_randomly_initialized_survey_scenario(reform=modify_social_security_taxation)
    aggregates = AbstractAggregates(survey_scenario=survey_scenario)
    aggregates.amount_unit = 1.0
    aggregates.beneficiaries_unit = 1.0
    return survey_scenario, aggregates


def test_aggregates(aggregates_test_setup):
    survey_scenario, aggregates = aggregates_test_setup
    period = "2017-01"
    variables = ["social_security_contribution", "salary"]
    aggregates.aggregate_variables = variables

    df = aggregates.compute_aggregates(reform=True, actual=False)

    for variable in variables:
        aggregate_before = survey_scenario.compute_aggregate(variable, period=period, use_baseline=True)
        aggregate_after = survey_scenario.compute_aggregate(variable, period=period)
        assert df.loc[variable, "baseline_amount"] == int(aggregate_before)
        assert df.loc[variable, "reform_amount"] == int(aggregate_after)


def test_aggregates_winners_losers(aggregates_test_setup):
    survey_scenario, aggregates = aggregates_test_setup
    period = "2017-01"
    variable = "social_security_contribution"
    aggregates.aggregate_variables = [variable]

    df = aggregates.get_data_frame(target='reform', default='baseline')

    assert 'Gagnants' in df.columns
    assert 'Perdants' in df.columns
    assert 'Neutres' in df.columns

    stats = survey_scenario.simulations['reform'].compute_winners_losers(
        baseline_simulation=survey_scenario.simulations['baseline'],
        variable=variable,
        period=period
    )

    assert df.loc[0, 'Gagnants'] == str(int(round(stats['above_after'])))
    assert df.loc[0, 'Perdants'] == str(int(round(stats['lower_after'])))
    assert df.loc[0, 'Neutres'] == str(int(round(stats['neutral'])))
