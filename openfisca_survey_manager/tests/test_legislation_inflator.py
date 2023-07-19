

from openfisca_core import periods
from openfisca_country_template import CountryTaxBenefitSystem
from openfisca_survey_manager.utils import inflate_parameters, parameters_asof


def test_asof_simple_annual_parameter():
    """
        Test parameters_asof on a simple parameter
    """
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    income_tax_rate_2014 = parameters.taxes.income_tax_rate(2014)
    income_tax_rate_2015 = parameters.taxes.income_tax_rate(2015)
    assert income_tax_rate_2015 != income_tax_rate_2014
    parameters_asof(parameters, instant = "2014")
    assert parameters.taxes.income_tax_rate(2014) == income_tax_rate_2014, "{} != {}".format(
        parameters.taxes.income_tax_rate(2014), income_tax_rate_2014)
    assert parameters.taxes.income_tax_rate(2015) == income_tax_rate_2014, "{} != {}".format(
        parameters.taxes.income_tax_rate(2015), income_tax_rate_2014)


def test_asof_scale_parameters():
    """
        Test parameters_asof on a scale parameter
    """
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    social_security_contribution_2016 = parameters.taxes.social_security_contribution(2016).thresholds[1]
    social_security_contribution_2017 = parameters.taxes.social_security_contribution(2017).thresholds[1]
    assert social_security_contribution_2016 != social_security_contribution_2017
    parameters_asof(parameters, instant = "2016")
    assert parameters.taxes.social_security_contribution(2016).thresholds[1] == social_security_contribution_2016
    assert parameters.taxes.social_security_contribution(2017).thresholds[1] == social_security_contribution_2016


def test_inflate_simple_parameter():
    """
        Test parameters inflator on a simple parameter as the basic income
    """
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    basic_income_2016 = parameters.benefits.basic_income(2016)
    basic_income_2017 = parameters.benefits.basic_income(2017)
    assert basic_income_2017 == basic_income_2016
    inflate_parameters(parameters, inflator = .1, base_year = 2016, last_year = 2017)

    assert basic_income_2016 == parameters.benefits.basic_income(2016)
    assert 1.1 * basic_income_2016 == parameters.benefits.basic_income(2017)


def test_inflate_scale():
    """
        Test parameters inflator on a scale parameter as the social security contributions tax_scale
    """
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    inflate_parameters(parameters, inflator = .3, base_year = 2015, last_year = 2016)
    for (threshold_2016, threshold_2015) in zip(
            parameters.taxes.social_security_contribution(2016).thresholds,
            parameters.taxes.social_security_contribution(2015).thresholds
            ):
        assert threshold_2016 == threshold_2015 * 1.3


def test_inflate_scale_with_changing_number_of_brackets():
    """
        Test parameters inflator on a scale parameter when the number of brackets changes

        Use parameters_asof to use the present legislation the future pre-inflated legislation
        Test on the social security contributions tax_scale
    """
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    parameters_asof(parameters, instant = periods.instant(2016))  # Remove post 2016 legislation changes
    inflate_parameters(parameters, inflator = .3, base_year = 2016, last_year = 2017)
    for (threshold_2017, threshold_2016) in zip(
            parameters.taxes.social_security_contribution(2017).thresholds,
            parameters.taxes.social_security_contribution(2016).thresholds
            ):
        assert threshold_2017 == threshold_2016 * 1.3, "{} != {}".format(
            threshold_2017, threshold_2016 * 1.3
            )


def test_inflate_start_instant_option():
    """
        Test parameters inflator with a specific start_instant
    """
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    parameters_asof(parameters, instant = periods.instant(2022))  # Remove post 2022 legislation changes
    inflate_parameters(parameters, inflator = .3, base_year = 2022, last_year = 2023, start_instant="2023-07-01")
    for (threshold_2023_06, threshold_2023_07, threshold_2022) in zip(
            parameters.taxes.social_security_contribution('2023-06').thresholds,
            parameters.taxes.social_security_contribution('2023-07').thresholds,
            parameters.taxes.social_security_contribution(2022).thresholds
            ):
        assert threshold_2023_07 == threshold_2022 * 1.3, "{} != {}".format(
            threshold_2023_07, threshold_2022 * 1.3
            )
        assert threshold_2023_06 == threshold_2022, "{} != {}".format(
            threshold_2023_06, threshold_2022
            )


if __name__ == '__main__':
    test_inflate_simple_parameter()
    test_inflate_scale()
    test_inflate_scale_with_changing_number_of_brackets()
    test_asof_simple_annual_parameter()
    test_asof_scale_parameters()
    test_inflate_start_instant_option()
