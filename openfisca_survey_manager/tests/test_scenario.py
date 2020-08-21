
import shutil


import logging
import os
import pkg_resources


from openfisca_core.model_api import *  # noqa analysis:ignore
from openfisca_core import periods
from openfisca_core.tools import assert_near

from openfisca_country_template import CountryTaxBenefitSystem


from openfisca_survey_manager.input_dataframe_generator import (
    make_input_dataframe_by_entity,
    random_data_generator,
    randomly_init_variable,
    )
from openfisca_survey_manager.scenarios import AbstractSurveyScenario


log = logging.getLogger(__name__)


tax_benefit_system = CountryTaxBenefitSystem()


def create_randomly_initialized_survey_scenario(nb_persons = 10, nb_groups = 5, salary_max_value = 50000,
        rent_max_value = 1000, collection = "test_random_generator", use_marginal_tax_rate = False):
    if collection is not None:
        return create_randomly_initialized_survey_scenario_from_table(
            nb_persons, nb_groups, salary_max_value, rent_max_value, collection, use_marginal_tax_rate)
    else:
        return create_randomly_initialized_survey_scenario_from_data_frame(
            nb_persons, nb_groups, salary_max_value, rent_max_value, use_marginal_tax_rate)


def create_randomly_initialized_survey_scenario_from_table(nb_persons, nb_groups, salary_max_value, rent_max_value, collection, use_marginal_tax_rate):
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
        periods.period('2018-01'): [
            {
                'variable': 'salary',
                'max_value': salary_max_value,
                },
            ],
        }
    table_by_entity_by_period = random_data_generator(tax_benefit_system, nb_persons, nb_groups,
        variable_generators_by_period, collection)
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(tax_benefit_system = tax_benefit_system)
    survey_scenario.used_as_input_variables = ['salary', 'rent', 'housing_occupancy_status']
    survey_scenario.year = 2017
    survey_scenario.collection = collection
    data = {
        'survey': 'input',
        'input_data_table_by_entity_by_period': table_by_entity_by_period
        }
    survey_scenario.varying_variable = 'salary'
    survey_scenario.init_from_data(data = data, use_marginal_tax_rate = use_marginal_tax_rate)
    return survey_scenario


def create_randomly_initialized_survey_scenario_from_data_frame(nb_persons, nb_groups, salary_max_value, rent_max_value, use_marginal_tax_rate = False):
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(tax_benefit_system = tax_benefit_system)
    survey_scenario.year = 2017
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    period = periods.period('2017-01')
    data = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            }
        }
    survey_scenario.varying_variable = 'salary'
    survey_scenario.init_from_data(data = data, use_marginal_tax_rate = use_marginal_tax_rate)
    return survey_scenario


def generate_input_input_dataframe_by_entity(nb_persons, nb_groups, salary_max_value, rent_max_value):
    input_dataframe_by_entity = make_input_dataframe_by_entity(tax_benefit_system, nb_persons, nb_groups)
    randomly_init_variable(
        tax_benefit_system,
        input_dataframe_by_entity,
        'salary',
        max_value = salary_max_value,
        condition = "household_role == 'first_parent'"
        )
    randomly_init_variable(
        tax_benefit_system,
        input_dataframe_by_entity,
        'rent',
        max_value = rent_max_value
        )
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

    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(tax_benefit_system = tax_benefit_system)
    survey_scenario.year = 2017
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    period = periods.period('2017-01')
    data = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            }
        }
    survey_scenario.init_from_data(data = data)

    simulation = survey_scenario.simulation
    assert (
        simulation.calculate('salary', period) == input_data_frame_by_entity['person']['salary']
        ).all()
    assert (
        simulation.calculate('rent', period) == input_data_frame_by_entity['household']['rent']
        ).all()


def test_survey_scenario_input_dataframe_import_scrambled_ids(nb_persons = 10, nb_groups = 5, salary_max_value = 50000,
        rent_max_value = 1000):
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)
    input_data_frame_by_entity['person']['household_id'] = 4 - input_data_frame_by_entity['person']['household_id']
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(tax_benefit_system = tax_benefit_system)
    survey_scenario.year = 2017
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    period = periods.period('2017-01')
    data = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            }
        }
    survey_scenario.init_from_data(data = data)
    simulation = survey_scenario.simulation
    period = periods.period('2017-01')
    assert (
        simulation.calculate('salary', period) == input_data_frame_by_entity['person']['salary']
        ).all()
    assert (
        simulation.calculate('rent', period) == input_data_frame_by_entity['household']['rent']
        ).all()


def test_dump_survey_scenario():
    survey_scenario = create_randomly_initialized_survey_scenario()
    directory = os.path.join(
        pkg_resources.get_distribution('openfisca-survey-manager').location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        'dump',
        )
    if os.path.exists(directory):
        shutil.rmtree(directory)
    survey_scenario.dump_simulations(directory = directory)
    df = survey_scenario.create_data_frame_by_entity(variables = ['salary', 'rent'])
    household = df['household']
    person = df['person']
    assert not household.empty
    assert not person.empty
    del survey_scenario
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(tax_benefit_system = tax_benefit_system)
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    survey_scenario.year = 2017
    survey_scenario.restore_simulations(directory = directory)
    df2 = survey_scenario.create_data_frame_by_entity(variables = ['salary', 'rent'], period = '2017-01')

    assert (df2['household'] == household).all().all()
    assert (df2['person'] == person).all().all()


def test_inflate():
    survey_scenario = create_randomly_initialized_survey_scenario()
    period = "2017-01"
    inflator = 2.42
    inflator_by_variable = {'rent': inflator}

    rent_before_inflate = survey_scenario.compute_aggregate('rent', period = period)
    survey_scenario.inflate(inflator_by_variable = inflator_by_variable, period = period)
    rent_after_inflate = survey_scenario.compute_aggregate('rent', period = period)

    assert_near(
        rent_after_inflate,
        inflator * rent_before_inflate,
        relative_error_margin = 1e-6,
        message = "Failing inflate with inflator_by_variable: rent_after_inflate = {} != {} = rent_before_inflate ({}) x inflator ({})".format(
            rent_after_inflate,
            rent_before_inflate * inflator,
            rent_before_inflate,
            inflator
            )
        )

    target = 3e5
    target_by_variable = {'salary': target}
    salary_before_inflate = survey_scenario.compute_aggregate('salary', period = period)
    survey_scenario.inflate(target_by_variable = target_by_variable, period = period)
    salary_after_inflate = survey_scenario.compute_aggregate('salary', period = period)
    assert_near(
        salary_after_inflate,
        target,
        relative_error_margin = 1e-6,
        message = "Failing inflate with inflator_by_variable: salary_after_inflate = {} != {} = target (salary_before_inflate = {})\n".format(
            salary_after_inflate,
            target,
            salary_before_inflate,
            )
        )


if __name__ == "__main__":
    import sys
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_inflate()
    # test_create_data_frame_by_entity()
