from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
from openfisca_country_template.reforms.modify_social_security_taxation import modify_social_security_taxation


def test_compute_pivot_table():
    survey_scenario = create_randomly_initialized_survey_scenario(reform = modify_social_security_taxation)
    period = "2017-01"

    return survey_scenario.compute_pivot_table(
        aggfunc = "mean",
        columns = ['age'],
        difference = False,
        filter_by = None,
        index = None,
        period = period,
        use_baseline = True,
        use_baseline_for_columns = True,
        values = ['salary'],
        missing_variable_default_value = 0,
        concat_axis = None,
        weighted = True,
        alternative_weights = None,
        )
