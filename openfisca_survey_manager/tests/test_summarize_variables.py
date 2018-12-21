# -*- coding: utf-8 -*-


import logging

from openfisca_core import periods
from openfisca_survey_manager.input_dataframe_generator import (
    make_input_dataframe_by_entity,
    random_data_generator,
    randomly_init_variable,
    )
from openfisca_country_template import CountryTaxBenefitSystem
from openfisca_survey_manager.scenarios import AbstractSurveyScenario

from openfisca_survey_manager.tests.test_scenario import test_random_data_generator

log = logging.getLogger(__name__)


tax_benefit_system = CountryTaxBenefitSystem()



def test_summarize_variable():
    survey_scenario = test_random_data_generator()
    survey_scenario.summarize_variable(variable = "rent", force_compute = True)
    survey_scenario.summarize_variable(variable = "housing_occupancy_status", force_compute = True)


if __name__ == "__main__":
    import sys
    import pandas as pd
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_summarize_variable()
