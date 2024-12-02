
import logging


from openfisca_core.tools import assert_near
from openfisca_country_template import CountryTaxBenefitSystem
from openfisca_survey_manager.tests.test_scenario import (
    create_randomly_initialized_survey_scenario
    )


log = logging.getLogger(__name__)


tax_benefit_system = CountryTaxBenefitSystem()


def test_compute_marginal_tax_rate():
    survey_scenario = create_randomly_initialized_survey_scenario(use_marginal_tax_rate = True)
    assert "_modified_baseline" in survey_scenario.simulations
    assert_near(
        survey_scenario.compute_marginal_tax_rate(target_variable = 'income_tax', period = 2017, simulation = "baseline"),
        (1 - .15),
        relative_error_margin = 1e-6,
        )
    # survey_scenario.compute_marginal_tax_rate(target_variable = 'disposable_income', period = 2017, simulation = "baseline")


if __name__ == "__main__":
    import sys
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_compute_marginal_tax_rate()
