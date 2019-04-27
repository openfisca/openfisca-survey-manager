# -*- coding: utf-8 -*-


import pytest

from openfisca_france.france_taxbenefitsystem import FranceTaxBenefitSystem
from openfisca_france_data import france_data_tax_benefit_system
from openfisca_france_data.erfs_fpr.get_survey_scenario import get_survey_scenario
from openfisca_france_data.aggregates import Aggregates


@pytest.fixture
def tax_benefit_system() -> FranceTaxBenefitSystem:
    return france_data_tax_benefit_system


def test_calculate_variable(tax_benefit_system, year = 2014, rebuild_input_data = False):
    survey_scenario = get_survey_scenario(
        tax_benefit_system = tax_benefit_system,
        baseline_tax_benefit_system = tax_benefit_system,
        year = year,
        rebuild_input_data = rebuild_input_data,
        )

    assert survey_scenario.calculate_variable('aides_logement', period = year)


def test_compute_aggregates(tax_benefit_system, year = 2014, rebuild_input_data = False):
    survey_scenario = get_survey_scenario(
        tax_benefit_system = tax_benefit_system,
        baseline_tax_benefit_system = tax_benefit_system,
        year = year,
        rebuild_input_data = rebuild_input_data,
        )

    aggregates = Aggregates(survey_scenario = survey_scenario)

    assert aggregates.compute_aggregates(use_baseline = True, actual = False)
