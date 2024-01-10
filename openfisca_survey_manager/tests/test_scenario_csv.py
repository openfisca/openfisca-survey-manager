import logging
import os
import pandas as pd
import pkg_resources

from openfisca_core.model_api import *  # noqa analysis:ignore
from openfisca_core import periods
from openfisca_country_template import CountryTaxBenefitSystem
from openfisca_survey_manager.tests.test_scenario import generate_input_input_dataframe_by_entity
from openfisca_survey_manager.scenarios import AbstractSurveyScenario


log = logging.getLogger(__name__)
tax_benefit_system = CountryTaxBenefitSystem()
directory = os.path.join(
    pkg_resources.get_distribution('openfisca-survey-manager').location,
    'openfisca_survey_manager',
    'tests',
    'data_files',
    'dump',
    )


def create_entity_csv_files():
    input_dataframe_by_entity = generate_input_input_dataframe_by_entity(nb_persons = 10, nb_groups = 5, salary_max_value = 50000,
        rent_max_value = 1000)
    for entity, dataframe in input_dataframe_by_entity.items():
        dataframe.to_csv(os.path.join(directory, "{}.csv".format(entity)), index = False)


def test_survey_scenario_csv_import():
    create_entity_csv_files()
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(tax_benefit_system = tax_benefit_system)
    survey_scenario.year = 2017
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    period = periods.period('2017-01')
    survey_scenario.tax_benefit_system.entities
    input_data_frame_by_entity = dict()
    for entity in survey_scenario.tax_benefit_system.entities:
        entity_key = entity.key
        dataframe = pd.read_csv(os.path.join(directory, "{}.csv".format(entity_key)))
        input_data_frame_by_entity[entity_key] = dataframe

    data = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            }
        }
    survey_scenario.init_from_data(data = data)
    simulation = survey_scenario.simulation
    error = 2e-03
    assert (
        (simulation.calculate('salary', period) - input_data_frame_by_entity['person']['salary']).abs()
        < error).all()
    assert (
        (simulation.calculate('rent', period) - input_data_frame_by_entity['household']['rent']).abs()
        < error).all()


if __name__ == "__main__":
    import sys
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_survey_scenario_csv_import()
