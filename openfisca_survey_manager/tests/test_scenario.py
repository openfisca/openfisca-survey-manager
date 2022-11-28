
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


# On vérifie que l'attribut `used_as_input_variables` correspond à la liste des variables
# qui sont employées dans le calcul des simulations, les autres variables n'étant pas utilisées dans le calcul,
# étant dans la base en entrée mais pas dans la base en sortie (la base de la simulation)
def test_init_from_data(nb_persons = 10, nb_groups = 5, salary_max_value = 50000,
        rent_max_value = 1000):

    # Set up test : the minimum necessary data to perform an `init_from_data`
    survey_scenario = AbstractSurveyScenario()
    # Generate some data and its period
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)
    period = periods.period('2017-01')
    # Creating a data object associated to its period, and we give it a name
    data_in = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            }
        }
    # data_in = copy.deepcopy(data_in) # Pour comparer avec la sortie de `init_from_data`
    table_ind = input_data_frame_by_entity['person'].copy(deep=True)
    table_men = input_data_frame_by_entity['household'].copy(deep=True)
    # print(table_ind)

    # We must add a TBS to the scenario to indicate what are the entities
    survey_scenario.set_tax_benefit_systems(tax_benefit_system = tax_benefit_system)
    # We must add the `used_as_input_variables` even though they don't seem necessary
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    # We must add the year to initiate a .new_simulation
    survey_scenario.year = 2017
    # Then we can input the data+period dict inside the scenario
    survey_scenario.init_from_data(data = data_in)

    # We are looking for the dataframes inside the survey_scenario
    all_var = list(set(list(table_ind.columns) + list(table_men.columns)))
    # print('Variables', all_var)
    data_out = survey_scenario.create_data_frame_by_entity(variables = all_var, period = period, merge = False)
    # data_out =  survey_scenario.create_data_frame_by_entity(variables = all_var, period = period, merge = True)

    # 1 - Has the data object changed ? We only compare variables because Id's and others are lost in the process
    for cols in table_ind:
        if cols in data_out['person']:
            pass
        else:
            print('Columns lost in person table: ', cols)
    assert data_out['person']['salary'].equals(table_ind['salary'])

    for cols in table_men:
        if cols in data_out['household']:
            pass
        else:
            print('Columns lost in household table: ', cols)
    assert data_out['household']['rent'].equals(table_men['rent'])


# def test_used_as_input_variables():
#    # Set up test
#    #
#    #
#
#
#    ## test filter_input_variables OU quelle fct pour tester used_as_input_variables ?
#    # 2 - If we filter the input variables, are they still in the database?
#    survey_scenario.used_as_input_variables = ['rent']
#    survey_scenario.filter_input_variables()
#
#    assert 'rent' in base
#    assert 'salary' not base
#
#    # 3 - Faut-il recalculer la base?
#    base2 = survey_scenario.input_data_table_by_period  # ??
#    assert base2 == base
#
#    # 4 - If we perform a simulation, are they still in the database?
#    survey do simulation


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
    '''
        On teste que .init_from_data fait
    '''
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)  # Un dataframe d'exemple que l'on injecte
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
