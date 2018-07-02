# -*- coding: utf-8 -*-


from openfisca_france import FranceTaxBenefitSystem
from openfisca_survey_manager.utils import inflate_parameters


def test_inflate_simple_parameter():
    tax_benefit_system = FranceTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    pt_ind_2014 = parameters.cotsoc.sal.fonc.commun.pt_ind(2014)
    pt_ind_2015 = parameters.cotsoc.sal.fonc.commun.pt_ind(2015)
    assert pt_ind_2014 == pt_ind_2015
    inflate_parameters(parameters, inflator = .1, base_year = 2014, last_year = 2015)
    print(parameters.cotsoc.sal.fonc.commun.pt_ind)

    assert pt_ind_2014 == parameters.cotsoc.sal.fonc.commun.pt_ind(2014)
    assert 1.1 * pt_ind_2014 == parameters.cotsoc.sal.fonc.commun.pt_ind(2015)


def test_inflate_scale():
    tax_benefit_system = FranceTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    inflate_parameters(parameters, inflator = .1, base_year = 2016, last_year = 2017)
    for (threshold_2017, threshold_2016) in zip(
            parameters.impot_revenu.bareme(2017).thresholds,
            parameters.impot_revenu.bareme(2016).thresholds
            ):
        assert threshold_2017 == threshold_2016 * 1.1


if __name__ == '__main__':
    test_inflate_simple_parameter()
    test_inflate_scale()

