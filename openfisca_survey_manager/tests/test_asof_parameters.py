# -*- coding: utf-8 -*-


from openfisca_france import FranceTaxBenefitSystem
from openfisca_survey_manager.utils import parameters_asof


def test_asof_simple_annual_parameter():
    tax_benefit_system = FranceTaxBenefitSystem()
    parameters = tax_benefit_system.parameters

    plafond_quotient_familial_2016 = parameters.impot_revenu.plafond_qf.general(2016)
    plafond_quotient_familial_2017 = parameters.impot_revenu.plafond_qf.general(2017)
    assert plafond_quotient_familial_2016 != plafond_quotient_familial_2017

    parameters_asof(parameters, instant = "2016")
    assert parameters.impot_revenu.plafond_qf.general(2016) == plafond_quotient_familial_2016
    assert parameters.impot_revenu.plafond_qf.general(2017) == plafond_quotient_familial_2016


def test_asof_scale_parameters():
    tax_benefit_system = FranceTaxBenefitSystem()
    parameters = tax_benefit_system.parameters

    bareme_impot_2016 = parameters.impot_revenu.bareme(2016).thresholds[2]
    bareme_impot_2017 = parameters.impot_revenu.bareme(2017).thresholds[2]
    assert bareme_impot_2016 != bareme_impot_2017

    parameters_asof(parameters, instant = "2016")
    assert parameters.impot_revenu.bareme(2016).thresholds[2] == bareme_impot_2016
    assert parameters.impot_revenu.bareme(2017).thresholds[2] == bareme_impot_2016


if __name__ == "__main__":
    test_asof_simple_annual_parameter()
    test_asof_scale_parameters()
