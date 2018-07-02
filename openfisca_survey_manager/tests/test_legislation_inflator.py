# -*- coding: utf-8 -*-


# from openfisca_france import FranceTaxBenefitSystem
from openfisca_country_template import CountryTaxBenefitSystem
from openfisca_survey_manager.utils import inflate_parameters


def test_inflate_simple_parameter():
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    basic_income_2016 = parameters.benefits.basic_income(2016)
    basic_income_2017 = parameters.benefits.basic_income(2017)
    assert basic_income_2017 == basic_income_2016
    inflate_parameters(parameters, inflator = .1, base_year = 2016, last_year = 2017)

    assert basic_income_2016 == parameters.benefits.basic_income(2016)
    assert 1.1 * basic_income_2016 == parameters.benefits.basic_income(2017)


def test_inflate_scale():
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    inflate_parameters(parameters, inflator = .3, base_year = 2015, last_year = 2016)
    for (threshold_2016, threshold_2015) in zip(
            parameters.taxes.social_security_contribution(2016).thresholds,
            parameters.taxes.social_security_contribution(2015).thresholds
            ):
        assert threshold_2016 == threshold_2015 * 1.3

    # TODO use 2016 and 2017 to test the case of changing number of brackets

# def test_inflate_simple_parameter_france():
#     tax_benefit_system = FranceTaxBenefitSystem()
#     parameters = tax_benefit_system.parameters
#     pt_ind_2014 = parameters.cotsoc.sal.fonc.commun.pt_ind(2014)
#     pt_ind_2015 = parameters.cotsoc.sal.fonc.commun.pt_ind(2015)
#     assert pt_ind_2014 == pt_ind_2015
#     inflate_parameters(parameters, inflator = .1, base_year = 2014, last_year = 2015)
#     print(parameters.cotsoc.sal.fonc.commun.pt_ind)

#     assert pt_ind_2014 == parameters.cotsoc.sal.fonc.commun.pt_ind(2014)
#     assert 1.1 * pt_ind_2014 == parameters.cotsoc.sal.fonc.commun.pt_ind(2015)


# def test_inflate_scale_france():
#     tax_benefit_system = FranceTaxBenefitSystem()
#     parameters = tax_benefit_system.parameters
#     inflate_parameters(parameters, inflator = .1, base_year = 2016, last_year = 2017)
#     for (threshold_2017, threshold_2016) in zip(
#             parameters.impot_revenu.bareme(2017).thresholds,
#             parameters.impot_revenu.bareme(2016).thresholds
#             ):
#         assert threshold_2017 == threshold_2016 * 1.1


if __name__ == '__main__':
    test_inflate_simple_parameter()
    test_inflate_scale()
