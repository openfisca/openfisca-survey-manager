

from openfisca_core import periods
from openfisca_core.parameters import ParameterNode, Scale
from openfisca_country_template import CountryTaxBenefitSystem
from openfisca_survey_manager.utils import parameters_asof, variables_asof


def check_max_instant_leaf(sub_parameter, instant):
    for parameter_at_instant in sub_parameter.values_list:
        assert periods.instant(parameter_at_instant.instant_str) <= instant, f"Error for {sub_parameter.name}: \n {sub_parameter.values_list}"


def check_max_instant(parameters, instant):
    for _, sub_parameter in parameters.children.items():
        if isinstance(sub_parameter, ParameterNode):
            check_max_instant(sub_parameter, instant)
        else:
            if isinstance(sub_parameter, Scale):
                for bracket in sub_parameter.brackets:
                    threshold = bracket.children['threshold']
                    rate = bracket.children['rate']
                    check_max_instant_leaf(threshold, instant)
                    check_max_instant_leaf(rate, instant)
            else:
                check_max_instant_leaf(sub_parameter, instant)


def test_parameters_as_of():
    tax_benefit_system = CountryTaxBenefitSystem()
    parameters = tax_benefit_system.parameters
    instant = periods.instant("2012-12-31")
    parameters_asof(parameters, instant)
    check_max_instant(parameters, instant)


def test_variables_as_of():
    tax_benefit_system = CountryTaxBenefitSystem()
    instant = periods.instant("2015-12-31")
    variables_asof(tax_benefit_system, instant)


if __name__ == '__main__':
    test_parameters_as_of()
    test_variables_as_of()
