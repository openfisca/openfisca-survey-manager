# -*- coding: utf-8 -*-


import logging


from openfisca_survey_manager.input_dataframe_generator import (
    make_input_dataframe_by_entity,
    randomly_init_variable,
    )
from openfisca_country_template import CountryTaxBenefitSystem


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
    survey_scenario.init_from_data()
    simulation = survey_scenario.simulation

    for entity, input_dataframe in input_dataframe_by_entity.iteritems():
        print entity, input_dataframe
        survey_scenario.init_entity_with_data_frame(
            entity = entity,
            input_data_frame = input_dataframe,
            period = 2017,
            simulation = simulation,
            )


if __name__ == "__main__":
    import logging
    import sys
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_survey_scenario_input_dataframe_import()