# -*- coding: utf-8 -*-

import shutil


import logging
import os
import pkg_resources


from openfisca_core.model_api import *  # noqa analysis:ignore
from openfisca_core import periods
from openfisca_country_template import CountryTaxBenefitSystem


from openfisca_survey_manager.tests.test_scenario import (
    create_randomly_initialized_survey_scenario
    )
from openfisca_survey_manager.scenarios import AbstractSurveyScenario


log = logging.getLogger(__name__)


tax_benefit_system = CountryTaxBenefitSystem()


def test_compute_marginal_tax_rate():
    survey_scenario = create_randomly_initialized_survey_scenario(use_marginal_tax_rate = True)
    assert survey_scenario._modified_simulation is not None
    # TODO clean this
    x = survey_scenario.compute_marginal_tax_rate(target_variable = 'income_tax', period = 2017)
    x = survey_scenario.compute_marginal_tax_rate(target_variable = 'disposable_income', period = 2017)


if __name__ == "__main__":
    import sys
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_compute_marginal_tax_rate()
