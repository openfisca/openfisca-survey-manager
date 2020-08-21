

import logging

from openfisca_country_template import CountryTaxBenefitSystem
from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario

log = logging.getLogger(__name__)


tax_benefit_system = CountryTaxBenefitSystem()


def test_summarize_variable():
    survey_scenario = create_randomly_initialized_survey_scenario()
    survey_scenario.summarize_variable(variable = "rent", force_compute = True)
    survey_scenario.summarize_variable(variable = "housing_occupancy_status", force_compute = True)


if __name__ == "__main__":
    # log = logging.getLogger(__name__)
    # logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_summarize_variable()
