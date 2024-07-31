"""Tests for the survey scenario functionality in OpenFisca Survey Manager."""

import shutil
import logging
import os
import pytest
from typing import Dict, Any, List, Optional, Callable


from openfisca_core import periods
from openfisca_core.tools import assert_near


from openfisca_survey_manager import openfisca_survey_manager_location, default_config_files_directory
from openfisca_survey_manager.input_dataframe_generator import (
    make_input_dataframe_by_entity,
    random_data_generator,
    randomly_init_variable,
    )
from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario
from openfisca_survey_manager.scenarios.reform_scenario import ReformScenario
from openfisca_survey_manager.tests import tax_benefit_system


log = logging.getLogger(__name__)


def create_randomly_initialized_survey_scenario(
        nb_persons: int = 10,
        nb_groups: int = 5,
        salary_max_value: float = 50000,
        rent_max_value: float = 1000,
        collection: Optional[str] = "test_random_generator",
        use_marginal_tax_rate: bool = False,
        reform: Optional[Callable] = None
        ) -> AbstractSurveyScenario:
    """
    Create a randomly initialized survey scenario.

    Args:
        nb_persons (int): Number of persons
        nb_groups (int): Number of groups
        salary_max_value (float): Maximum salary value
        rent_max_value (float): Maximum rent value
        collection (Optional[str]): Collection name
        use_marginal_tax_rate (bool): Use marginal tax rate
        reform (Optional[Callable]): Reform function

    Returns:
        AbstractSurveyScenario: Initialized survey scenario
    """
    if collection is not None:
        return create_randomly_initialized_survey_scenario_from_table(
            nb_persons, nb_groups, salary_max_value, rent_max_value, collection, use_marginal_tax_rate, reform = reform)
    else:
        return create_randomly_initialized_survey_scenario_from_data_frame(
            nb_persons, nb_groups, salary_max_value, rent_max_value, use_marginal_tax_rate, reform = reform)


def create_randomly_initialized_survey_scenario_from_table(
        nb_persons: int,
        nb_groups: int,
        salary_max_value: float,
        rent_max_value: float,
        collection: str,
        use_marginal_tax_rate: bool,
        reform: Optional[Callable] = None
        ) -> AbstractSurveyScenario:
    """
    Create a randomly initialized survey scenario from a table.

    Args:
        nb_persons (int): Number of persons
        nb_groups (int): Number of groups
        salary_max_value (float): Maximum salary value
        rent_max_value (float): Maximum rent value
        collection (str): Collection name
        use_marginal_tax_rate (bool): Use marginal tax rate
        reform (Optional[Callable]): Reform function

    Returns:
        AbstractSurveyScenario: Initialized survey scenario
    """
    variable_generators_by_period = {
        periods.period('2017-01'): [
            {
                'variable': 'salary',
                'max_value': salary_max_value,
                },
            {
                'variable': 'rent',
                'max_value': rent_max_value,
                },
            {
                'variable': 'household_weight',
                'max_value': 100,
                },
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
    if reform is None:
        survey_scenario = AbstractSurveyScenario()
        survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
    else:
        survey_scenario = ReformScenario()
        survey_scenario.set_tax_benefit_systems(dict(
            reform = reform(tax_benefit_system),
            baseline = tax_benefit_system,
            ))

    survey_scenario.used_as_input_variables = ['salary', 'rent', 'housing_occupancy_status', 'household_weight']
    survey_scenario.period = 2017
    survey_scenario.collection = collection
    data = {
        'survey': 'input',
        'input_data_table_by_entity_by_period': table_by_entity_by_period,
        'config_files_directory': default_config_files_directory
        }
    if use_marginal_tax_rate:
        survey_scenario.varying_variable = 'salary'

    survey_scenario.weight_variable_by_entity = {
        "person": "person_weight",
        "household": "household_weight",
        }
    survey_scenario.init_from_data(data = data, use_marginal_tax_rate = use_marginal_tax_rate)
    return survey_scenario


def create_randomly_initialized_survey_scenario_from_data_frame(
        nb_persons: int,
        nb_groups: int,
        salary_max_value: float,
        rent_max_value: float,
        use_marginal_tax_rate: bool = False,
        reform: Optional[Callable] = None
        ) -> AbstractSurveyScenario:
    """
        Create a randomly initialized survey scenario from a data frame.

    Args:
        nb_persons (int): Number of persons
        nb_groups (int): Number of groups
        salary_max_value (float): Maximum salary value
        rent_max_value (float): Maximum rent value
        use_marginal_tax_rate (bool): Use marginal tax rate
        reform (Optional[Callable]): Reform function

    Returns:
        AbstractSurveyScenario: Initialized survey scenario
    """
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)
    for entity in input_data_frame_by_entity.keys():
        if entity == "person":
            input_data_frame_by_entity[entity]["household_id_ind"] = input_data_frame_by_entity[entity]["household_id"]
        if entity == "household":
            input_data_frame_by_entity[entity]["household_id"] = input_data_frame_by_entity[entity].index

    survey_scenario = AbstractSurveyScenario()
    weight_variable_by_entity = {
        "person": "person_weight",
        "household": "household_weight",
        }
    if reform is None:
        survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
    else:
        survey_scenario.set_tax_benefit_systems(dict(
            reform = reform(tax_benefit_system),
            baseline = tax_benefit_system,
            ))
    survey_scenario.period = 2017
    survey_scenario.used_as_input_variables = ['salary', 'rent', 'household_weight', 'household_id', 'household_id_ind']
    period = periods.period('2017-01')

    data = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            },
        'config_files_directory': default_config_files_directory
        }
    survey_scenario.set_weight_variable_by_entity(weight_variable_by_entity)
    assert survey_scenario.weight_variable_by_entity == weight_variable_by_entity
    survey_scenario.init_from_data(data = data)
    for simulation_name, simulation in survey_scenario.simulations.items():
        assert simulation.weight_variable_by_entity == weight_variable_by_entity, f"{simulation_name} weight_variable_by_entity does not match {weight_variable_by_entity}"
        assert (survey_scenario.calculate_series("household_weight", period, simulation = simulation_name) != 0).all()
    return survey_scenario


def generate_input_input_dataframe_by_entity(
        nb_persons: int,
        nb_groups: int,
        salary_max_value: float,
        rent_max_value: float
        ) -> Dict[str, Any]:
    """
    Generate input dataframe by entity with randomly initialized variables.

    Args:
        nb_persons (int): Number of persons
        nb_groups (int): Number of groups
        salary_max_value (float): Maximum salary value
        rent_max_value (float): Maximum rent value

    Returns:
        Dict[str, Any]: Input dataframe by entity
    """
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
    randomly_init_variable(
        tax_benefit_system,
        input_dataframe_by_entity,
        'household_weight',
        max_value = 100,
        )
    return input_dataframe_by_entity


def test_input_dataframe_generator(
        nb_persons: int = 10,
        nb_groups: int = 5,
        salary_max_value: float = 50000,
        rent_max_value: float = 1000
        ) -> None:
    """Test the input dataframe generator function."""
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
def test_init_from_data(
        nb_persons: int = 10,
        nb_groups: int = 5,
        salary_max_value: float = 50000,
        rent_max_value: float = 1000,
        ) -> None:
    """
    Test the initialization of data in the survey scenario.

    Args:
        nb_persons: Number of persons to generate in the test data.
        nb_groups: Number of household groups to generate.
        salary_max_value: Maximum value for randomly generated salaries.
        rent_max_value: Maximum value for randomly generated rents.
    """
    # Set up test : the minimum necessary data to perform an `init_from_data`
    survey_scenario = AbstractSurveyScenario()
    assert survey_scenario.simulations is None
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
    survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
    assert len(survey_scenario.tax_benefit_systems) == 1
    assert list(survey_scenario.tax_benefit_systems.keys()) == ["baseline"]
    assert survey_scenario.simulations is None
    # We must add the `used_as_input_variables` even though they don't seem necessary
    survey_scenario.used_as_input_variables = ['salary', 'rent', 'household_weight']
    # We must add the year to initiate a .new_simulation
    survey_scenario.period = 2017
    # Then we can input the data+period dict inside the scenario
    survey_scenario.init_from_data(data = data_in)
    assert len(survey_scenario.simulations) == 1
    # We are looking for the dataframes inside the survey_scenario
    all_var = list(set(list(table_ind.columns) + list(table_men.columns)))
    # print('Variables', all_var)
    data_out = survey_scenario.create_data_frame_by_entity(variables = all_var, period = period, merge = False)

    # 1 - Has the data object changed ? We only compare variables because Id's and others are lost in the process
    for cols in table_ind:
        if cols in data_out['person']:
            pass
        else:
            print('Columns lost in person table: ', cols)  # noqa T201
    assert data_out['person']['salary'].equals(table_ind['salary'])

    for cols in table_men:
        if cols in data_out['household']:
            pass
        else:
            print('Columns lost in household table: ', cols)  # noqa T201
    assert data_out['household']['rent'].equals(table_men['rent'])


def test_survey_scenario_input_dataframe_import(
        nb_persons: int = 10,
        nb_groups: int = 5,
        salary_max_value: float = 50000,
        rent_max_value: float = 1000,
        ) -> None:
    """
    Test the import of input dataframes into a survey scenario.

    Args:
        nb_persons: Number of persons to generate.
        nb_groups: Number of household groups.
        salary_max_value: Maximum salary value.
        rent_max_value: Maximum rent value.
    """
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
    survey_scenario.period = 2017
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    period = periods.period('2017-01')
    data = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            },
        'config_files_directory': default_config_files_directory
        }
    survey_scenario.init_from_data(data = data)

    simulation = survey_scenario.simulations["baseline"]
    assert (
        simulation.calculate('salary', period) == input_data_frame_by_entity['person']['salary']
        ).all()
    assert (
        simulation.calculate('rent', period) == input_data_frame_by_entity['household']['rent']
        ).all()


def test_survey_scenario_input_dataframe_import_scrambled_ids(
        nb_persons: int = 10,
        nb_groups: int = 5,
        salary_max_value: float = 50000,
        rent_max_value: float = 1000
        ) -> None:
    """
    Test survey scenario input dataframe import with scrambled IDs.

    Args:
        nb_persons: Number of persons to generate.
        nb_groups: Number of household groups.
        salary_max_value: Maximum salary value.
        rent_max_value: Maximum rent value.
    """
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value)  # Un dataframe d'exemple que l'on injecte
    input_data_frame_by_entity['person']['household_id'] = 4 - input_data_frame_by_entity['person']['household_id']
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
    survey_scenario.period = 2017
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    period = periods.period('2017-01')
    data = {
        'input_data_frame_by_entity_by_period': {
            period: input_data_frame_by_entity
            },
        'config_files_directory': default_config_files_directory
        }
    survey_scenario.init_from_data(data = data)
    simulation = survey_scenario.simulations["baseline"]
    period = periods.period('2017-01')
    assert (
        simulation.calculate('salary', period) == input_data_frame_by_entity['person']['salary']
        ).all()
    assert (
        simulation.calculate('rent', period) == input_data_frame_by_entity['household']['rent']
        ).all()


def test_dump_survey_scenario() -> None:
    """Test the dump and restore functionality of survey scenarios."""
    survey_scenario = create_randomly_initialized_survey_scenario()
    directory = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        'dump',
        )
    if os.path.exists(directory):
        shutil.rmtree(directory)

    survey_scenario.dump_simulations(directory = directory)
    period = "2017-01"
    df = survey_scenario.create_data_frame_by_entity(variables = ['salary', 'rent'], period = period)
    household = df['household']
    person = df['person']
    assert not household.empty
    assert not person.empty
    del survey_scenario
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems(dict(baseline = tax_benefit_system))
    survey_scenario.used_as_input_variables = ['salary', 'rent']
    survey_scenario.period = 2017
    survey_scenario.restore_simulations(directory = directory)
    df2 = survey_scenario.create_data_frame_by_entity(variables = ['salary', 'rent'], period = '2017-01')

    assert (df2['household'] == household).all().all()
    assert (df2['person'] == person).all().all()


@pytest.mark.order(before="test_add_survey_to_collection.py::test_add_survey_to_collection")
def test_inflate() -> None:
    """Test the inflate method of the survey scenario."""
    survey_scenario = create_randomly_initialized_survey_scenario(collection = None)
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


@pytest.mark.order(before="test_add_survey_to_collection.py::test_add_survey_to_collection")
def test_compute_pivot_table() -> None:
    """Test the compute_pivot_table method of the survey scenario."""
    survey_scenario = create_randomly_initialized_survey_scenario(collection = None)
    period = "2017-01"
    pivot_table = survey_scenario.compute_pivot_table(columns = ['age'], values = ["salary"], period = period, simulation = "baseline")

    assert pivot_table.index == "salary"
    assert pivot_table.values.round() == 21748

    del survey_scenario.weight_variable_by_entity
    survey_scenario.set_weight_variable_by_entity()
    pivot_table = survey_scenario.compute_pivot_table(columns = ['age'], values = ["salary"], period = period, simulation = "baseline")

    assert pivot_table.values.round() == 13570.


def test_compute_quantile() -> List[float]:
    """Test the compute_quantiles method of the survey scenario."""
    survey_scenario = create_randomly_initialized_survey_scenario()
    period = "2017-01"
    quintiles = survey_scenario.compute_quantiles(variable = "salary", nquantiles = 5, period = period, weighted = False, simulation = "baseline")
    return quintiles


if __name__ == "__main__":
    import sys
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    quintiles = test_compute_quantile()
    # pivot_table = test_compute_pivot_table()
    # test_inflate()
    # test_create_data_frame_by_entity()
