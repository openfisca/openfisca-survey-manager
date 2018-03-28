# -*- coding: utf-8 -*-


import logging

from openfisca_core.model_api import *  # noqa analysis:ignore
from openfisca_core import periods
from openfisca_survey_manager.input_dataframe_generator import (
    make_input_dataframe_by_entity,
    random_data_generator,
    randomly_init_variable,
    )
from openfisca_country_template import CountryTaxBenefitSystem



log = logging.getLogger(__name__)


tax_benefit_system = CountryTaxBenefitSystem()


def generate_input_input_dataframe_by_entity(nb_persons, nb_groups, salary_max_value, rent_max_value):
    input_dataframe_by_entity = make_input_dataframe_by_entity(tax_benefit_system, nb_persons, nb_groups)
    randomly_init_variable(
        tax_benefit_system, input_dataframe_by_entity, 'salary', 2017,
        max_value = salary_max_value,
        condition = "household_role == 'first_parent'")
    randomly_init_variable(tax_benefit_system, input_dataframe_by_entity, 'rent', 2017, max_value = rent_max_value)
    return input_dataframe_by_entity


def test_input_dataframe_generator(nb_persons = 10, nb_groups = 5, salary_max_value = 50000,
        rent_max_value = 1000):
    input_dataframe_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)
    assert (input_dataframe_by_entity['person']['household_role'] == "first_parent").sum() == 5
    assert (input_dataframe_by_entity['person'].loc[
        input_dataframe_by_entity['person']['household_role'] != "first_parent",
        'salary'
        ] == 0).all()

    assert (input_dataframe_by_entity['person'].loc[
        input_dataframe_by_entity['person']['household_role'] == "first_parent",
        'salary'
        ] > 0).all()
    assert (input_dataframe_by_entity['person'].loc[
        input_dataframe_by_entity['person']['household_role'] == "first_parent",
        'salary'
        ] <= salary_max_value).all()

    assert (input_dataframe_by_entity['household']['rent'] > 0).all()
    assert (input_dataframe_by_entity['household']['rent'] < rent_max_value).all()


def test_survey_scenario_input_dataframe_import(nb_persons = 10, nb_groups = 5, salary_max_value = 50000,
        rent_max_value = 1000):

    input_dataframe_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)
    from openfisca_survey_manager.scenarios import AbstractSurveyScenario
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(tax_benefit_system = tax_benefit_system)
    survey_scenario.year = 2017
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    survey_scenario.init_from_data()
    simulation = survey_scenario.simulation
    period = periods.period('2017-01')
    for entity, input_dataframe in input_dataframe_by_entity.iteritems():
        survey_scenario.init_entity_with_data_frame(
            entity = entity,
            input_data_frame = input_dataframe,
            period = period,
            simulation = simulation,
            )
    assert (
        simulation.calculate('salary', period) == input_dataframe_by_entity['person']['salary']
        ).all()
    assert (
        simulation.calculate('rent', period) == input_dataframe_by_entity['household']['rent']
        ).all()


def test_random_data_generator(nb_persons = 10, nb_groups = 5, salary_max_value = 50000,
        rent_max_value = 1000, collection = "toto"):
    import os
    import pkg_resources
    data_dir = os.path.join(
        pkg_resources.get_distribution('openfisca-survey-manager').location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )
    from openfisca_survey_manager.survey_collections import SurveyCollection
    variable_generators_by_period = {
        periods.period('2017-01'): [
            {
                'variable': 'salary',
                'max_value': salary_max_value,
                },
            {
                'variable': 'rent',
                'max_value': rent_max_value,
                }
            ],
        }
    random_data_generator(tax_benefit_system, nb_persons, nb_groups, variable_generators_by_period, collection)


    # input_dataframe_by_entity = generate_input_input_dataframe_by_entity(
    #     nb_persons, nb_groups, salary_max_value, rent_max_value)
    # period = periods.period('2017-01')



    # for entity, input_dataframe in input_dataframe_by_entity.iteritems():
    #     survey_scenario.init_entity_with_data_frame(
    #         entity = entity,
    #         input_data_frame = input_dataframe,
    #         period = period,
    #         simulation = simulation,
    #         )


if __name__ == "__main__":
    import sys
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_random_data_generator()
