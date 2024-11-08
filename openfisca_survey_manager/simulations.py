"""Monkey-patch openfisca_core.simulations.Simulation to work with pandas."""

import logging
import numpy as np
from numpy import logical_or as or_
import pandas as pd
import re
from typing import Callable, Dict, List, Optional, Union


import humanize
import warnings


from openfisca_core import periods
from openfisca_core.memory_config import MemoryConfig
from openfisca_core.indexed_enums import (Enum, EnumArray)
from openfisca_core.periods import ETERNITY, MONTH, YEAR
from openfisca_core.types import Array, CoreEntity as Entity, Period, TaxBenefitSystem
from openfisca_core.simulations import Simulation
from openfisca_survey_manager.simulation_builder import diagnose_variable_mismatch, SimulationBuilder
from openfisca_survey_manager.survey_collections import SurveyCollection


from openfisca_survey_manager.statshelpers import mark_weighted_percentiles
from openfisca_survey_manager.utils import do_nothing, load_table


log = logging.getLogger(__name__)


# Helpers

def assert_variables_in_same_entity(tax_benefit_system: TaxBenefitSystem, variables: List):
    """
    Assert that variables are in the same entity.

    Args:
        tax_benefit_system (TaxBenefitSystem): Host tax benefit system
        variables (List): Variables supposed to belong to the same entity

    Returns:
        str: Common entity of the variables
    """
    entity = None
    for variable_name in variables:
        variable = tax_benefit_system.variables.get(variable_name)
        assert variable
        if entity is None:
            entity = variable.entity
        assert variable.entity == entity, "{} are not from the same entity: {} doesn't belong to {}".format(
            variables, variable_name, entity.key)
    return entity.key


def get_words(text: str):
    return re.compile('[A-Za-z_]+').findall(text)


# Main functions

def adaptative_calculate_variable(simulation: Simulation, variable: str, period: Optional[Union[int, str, Period]]) -> Array:
    """
    Calculate variable by adpating it definition period to the target period.

    Args:
        simulation (Simulation): Simulation to suse
        variable (str): Variable to be computed
        period (Optional[Union[int, str, Period]]): Target period

    Returns:
        Array: Values of the variable on the target period
    """
    if not isinstance(period, periods.Period):
        period = periods.period(str(period))

    tax_benefit_system = simulation.tax_benefit_system
    assert tax_benefit_system is not None

    assert variable in tax_benefit_system.variables, "{} is not a valid variable".format(variable)
    period_size_independent = tax_benefit_system.get_variable(variable).is_period_size_independent
    definition_period = tax_benefit_system.get_variable(variable).definition_period

    if period_size_independent is False and definition_period != 'eternity':
        values = simulation.calculate_add(variable, period = period)
    elif period_size_independent is True and definition_period == 'month' and period.size_in_months > 1:
        values = simulation.calculate(variable, period = period.first_month)
    elif period_size_independent is True and definition_period == 'month' and period.size_in_months == 1:
        values = simulation.calculate(variable, period = period)
    elif period_size_independent is True and definition_period == 'year' and period.size_in_months > 12:
        values = simulation.calculate(variable, period = period.start.offset('first-of', 'year').period('year'))
    elif period_size_independent is True and definition_period == 'year' and period.size_in_months == 12:
        values = simulation.calculate(variable, period = period)
    elif period_size_independent is True and definition_period == 'year':
        values = simulation.calculate(variable, period = period.this_year)
    elif definition_period == 'eternity':
        values = simulation.calculate(variable, period = period)
    else:
        values = None
    assert values is not None, f"Unspecified calculation period for variable {variable}"

    return values


def compute_aggregate(simulation: Simulation, variable: str = None, aggfunc: str = 'sum', filter_by: str = None, period: Optional[Union[int, str, Period]] = None,
        missing_variable_default_value = np.nan, weighted: bool = True, alternative_weights: Optional[Union[str, int, float, Array]] = None,
        filtering_variable_by_entity: Dict = None) -> Optional[Union[None, float]]:
    """
    Compute aggregate of a variable.

    Args:
        simulation (Simulation): Simulation to use for the computation
        variable (str, optional): Variable to aggregate. Defaults to None.
        aggfunc (str, optional): Aggregation function. Defaults to 'sum'.
        filter_by (str, optional): Filter variable or expression to use. Defaults to None.
        period (Optional[Union[int, str, Period]], optional): Period. Defaults to None.
        missing_variable_default_value (optional): Value to use for missing values. Defaults to np.nan.
        weighted (bool, optional): Whether to weight the variable or not. Defaults to True.
        alternative_weights (Optional[Union[str, int, float, Array]], optional): Alternative weigh to use. Defaults to None.
        filtering_variable_by_entity (Dict, optional): Filtering variable by entity. Defaults to None.

    Returns:
        float: Aggregate
    """
    weight_variable_by_entity = simulation.weight_variable_by_entity
    tax_benefit_system = simulation.tax_benefit_system

    if period is None:
        period = simulation.period

    assert variable in tax_benefit_system.variables, f"{variable} is not a variable of the tax benefit system"
    entity_key = tax_benefit_system.variables[variable].entity.key

    if filter_by is None and filtering_variable_by_entity is not None:
        filter_by_variable = filtering_variable_by_entity.get(entity_key)

    if filter_by:
        filter_by_variable = get_words(filter_by)[0]
        assert filter_by_variable in tax_benefit_system.variables, f"{filter_by_variable} is not a variable of the tax benefit system"
        entity_key = tax_benefit_system.variables[variable].entity.key
        filter_by_entity_key = tax_benefit_system.variables[filter_by_variable].entity.key
        assert filter_by_entity_key == entity_key, (
            f"You tried to compute agregates for variable '{variable}', of entity {entity_key}"
            f" filtering by variable '{filter_by_variable}', of entity {filter_by_entity_key}. This is not possible."
            f" Please choose a filter-by variable of same entity as '{variable}'."
            )

    expressions = []
    if filter_by is not None:
        if filter_by in tax_benefit_system.variables:
            filter_entity_key = tax_benefit_system.variables.get(filter_by).entity.key
            assert filter_entity_key == entity_key, (
                "You tried to compute agregates for variable '{0}', of entity {1}"
                " filtering by variable '{2}', of entity {3}. This is not possible."
                " Please choose a filter-by variable of same entity as '{0}'.".format(
                    variable, entity_key, filter_by_variable, filter_by_entity_key
                    )
                )
        else:
            filter_entity_key = assert_variables_in_same_entity(tax_benefit_system, get_words(filter_by))
            expressions.extend([filter_by])
            assert filter_entity_key == entity_key
    else:
        filter_dummy = np.array(1.0)

    uniform_weight = np.array(1.0)
    weight_variable = None
    if weighted:
        assert or_(alternative_weights, weight_variable_by_entity), "The weighted option is set at True but there is no weight variable for entity {} nor alternative weights. Either define a weight variable or switch to unweighted".format(entity_key)
        if alternative_weights:
            if isinstance(alternative_weights, str):
                assert alternative_weights in tax_benefit_system.variables, \
                    f"{alternative_weights} is not a valid variable of the tax benefit system"
                weight_variable = alternative_weights

            elif (type(alternative_weights) is int) or (type(alternative_weights) is float):
                weight_variable = None
                uniform_weight = float(alternative_weights)
        elif weight_variable_by_entity:
            weight_variable = weight_variable_by_entity[entity_key]

    if variable in simulation.tax_benefit_system.variables:
        value = simulation.adaptative_calculate_variable(variable = variable, period = period)
    else:
        log.debug("Variable {} not found. Assigning {}".format(variable, missing_variable_default_value))
        return missing_variable_default_value

    weight = (
        simulation.adaptative_calculate_variable(weight_variable, period = period).astype(float)
        if weight_variable else uniform_weight
        )
    if weight_variable:
        assert any(weight != 0), "Weights shall not be all zeroes"
    else:
        assert uniform_weight != 0

    if filter_by is not None:
        expression_data_frame = simulation.create_data_frame_by_entity(
            variables = get_words(filter_by),
            period = period,
            index = False
            )[entity_key]
        for expression in expressions:
            expression_data_frame[expression] = expression_data_frame.eval(expression)

        filter_dummy = expression_data_frame[filter_by]
    else:
        filter_dummy = 1.0

    if aggfunc == 'sum':
        aggregate = (value * weight * filter_dummy).sum()
    elif aggfunc == 'mean':
        aggregate = (value * weight * filter_dummy).sum() / (weight * filter_dummy).sum()
    elif aggfunc == 'count':
        aggregate = (weight * filter_dummy).sum()
    elif aggfunc == 'count_non_zero':
        aggregate = (weight * (value != 0) * filter_dummy).sum()
    else:
        aggregate = None

    return aggregate


def compute_quantiles(simulation: Simulation, variable: str, nquantiles: int = None,
        period: Optional[Union[int, str, Period]] = None, filter_by = None, weighted: bool = True,
        alternative_weights = None, filtering_variable_by_entity = None) -> List[float]:
    """
    Compute quantiles of a variable.

    Args:
        simulation (Simulation, optional): Simulation to be used. Defaults to None.
        variable (str, optional): Variable which quantiles are computed. Defaults to None.
        nquantiles (int, optional): Number of quantiles. Defaults to None.
        period (Optional[Union[int, str, Period]], optional): Period. Defaults to None.
        missing_variable_default_value (optional): Value to use for missing values. Defaults to np.nan.
        weighted (bool, optional): Whether to weight the variable or not. Defaults to True.
        alternative_weights (Optional[Union[str, int, float, Array]], optional): Alternative weigh to use. Defaults to None.
        filtering_variable_by_entity (Dict, optional): Filtering variable by entity. Defaults to None.

    Returns:
       List(float): The quantiles values
    """
    weight_variable_by_entity = simulation.weight_variable_by_entity
    weight_variable = None
    entity_key = simulation.tax_benefit_system.variables[variable].entity.key
    if weight_variable_by_entity:
        weight_variable = weight_variable_by_entity[entity_key]

    variable_values = simulation.adaptative_calculate_variable(variable, period)
    if weighted:
        assert (alternative_weights is not None) or (weight_variable is not None)
        weight = (
            alternative_weights
            if alternative_weights is not None
            else simulation.calculate(weight_variable, period)
            )
    else:
        weight = np.ones(len(variable_values))

    if filtering_variable_by_entity is not None:
        if filter_by is None:
            filter_by = filtering_variable_by_entity.get(entity_key)

    if filter_by is not None:
        filter_entity_key = simulation.tax_benefit_system.variables.get(filter_by).entity.key
        assert filter_entity_key == entity_key
        filter_dummy = simulation.calculate(filter_by, period = period).astype(bool)

        variable_values = variable_values[filter_dummy].copy()
        weight = weight[filter_dummy].copy()

    labels = np.arange(1, nquantiles + 1)
    method = 2
    _, values = mark_weighted_percentiles(variable_values, labels, weight, method, return_quantiles = True)
    return values


def compute_pivot_table(simulation: Simulation = None, baseline_simulation: Simulation = None, aggfunc = 'mean',
        columns: Optional[List[str]] = None, difference: bool = False, filter_by = None, index: Optional[List[str]] = None,
        period: Optional[Union[int, str, Period]] = None, use_baseline_for_columns: bool = None, values: Optional[List[str]] = None,
        missing_variable_default_value = np.nan, concat_axis: Optional[int] = None, weighted: bool = True, alternative_weights = None,
        filtering_variable_by_entity = None):
    """
    Compute pivot table.

    Args:
        simulation (Simulation, optional): Main simulation. Defaults to None.
        baseline_simulation (Simulation, optional): Baseline simulation. Defaults to None.
        aggfunc (str, optional): Aggregation function. Defaults to 'mean'.
        columns (List[str], optional): Variables to use in columns. Defaults to None.
        difference (bool, optional): Whether to compute the difference with baseline. Defaults to False.
        filter_by (str, optional): Filter variable or expression to use. Defaults to None.
        index (List[str], optional): _description_. Defaults to None.
        period (Optional[Union[int, str, Period]], optional): Period. Defaults to None.
        use_baseline_for_columns (bool, optional): _description_. Defaults to None.
        values (List[str], optional): _description_. Defaults to None.
        missing_variable_default_value (optional): _description_. Defaults to np.nan.
        concat_axis (int, optional): _description_. Defaults to None.
        weighted (bool, optional): Whether to weight the variable or not. Defaults to True.
        alternative_weights (Optional[Union[str, int, float, Array]], optional): Alternative weigh to use. Defaults to None.
        filtering_variable_by_entity (Dict, optional): Filtering variable by entity. Defaults to None.

    Returns:
        _type_: _description_
    """
    weight_variable_by_entity = simulation.weight_variable_by_entity

    admissible_aggfuncs = ['max', 'mean', 'min', 'sum', 'count', 'sum_abs']
    assert aggfunc in admissible_aggfuncs
    assert columns or index or values

    if baseline_simulation is not None:
        tax_benefit_system = baseline_simulation.tax_benefit_system
    else:
        tax_benefit_system = simulation.tax_benefit_system

    assert period is not None

    if isinstance(columns, str):
        columns = [columns]
    elif columns is None:
        columns = []
    assert isinstance(columns, list)

    if isinstance(index, str):
        index = [index]
    elif index is None:
        index = []
    assert isinstance(index, list)

    if isinstance(values, str):
        values = [values]
    elif values is None:
        values = []
    assert isinstance(values, list)

    entity_key = None
    for axe in [columns, index, values]:
        if (len(axe) != 0) and (entity_key is None):
            entity_key = tax_benefit_system.variables[axe[0]].entity.key
            continue

    if filter_by is None and filtering_variable_by_entity is not None:
        filter_by = filtering_variable_by_entity.get(entity_key)

    variables = set(index + columns)

    # Select the entity weight corresponding to the variables that will provide values
    uniform_weight = 1.0
    weight_variable = None
    if weighted:
        if alternative_weights:
            if isinstance(alternative_weights, str):
                assert alternative_weights in tax_benefit_system.variables, \
                    f"{alternative_weights} is not a valid variable of the tax benefit system"
                weight_variable = alternative_weights

            elif (type(alternative_weights) is int) or (type(alternative_weights) is float):
                weight_variable = None
                uniform_weight = float(alternative_weights)

        else:
            if weight_variable_by_entity:
                weight_variable = weight_variable_by_entity[entity_key]
                variables.add(weight_variable)

            else:
                log.warn('There is no weight variable for entity {} nor alternative weights. Switch to unweighted'.format(entity_key))

    expressions = []
    if filter_by is not None:
        if filter_by in tax_benefit_system.variables:
            variables.add(filter_by)
            filter_entity_key = tax_benefit_system.variables.get(filter_by).entity.key
            assert filter_entity_key == entity_key
        else:
            filter_entity_key = assert_variables_in_same_entity(tax_benefit_system, get_words(filter_by))
            expressions.extend([filter_by])
            assert filter_entity_key == entity_key
    else:
        filter_dummy = np.array(1.0)

    for expression in expressions:
        expression_variables = get_words(expression)
        expression_entity_key = assert_variables_in_same_entity(tax_benefit_system, expression_variables)
        assert expression_entity_key == entity_key
        for variable in expression_variables:
            variables.add(variable)

    for variable in variables | set(values):
        if variable in tax_benefit_system.variables:
            assert tax_benefit_system.variables[variable].entity.key == entity_key, \
                'The variable {} does not belong to entity {}'.format(
                    variable,
                    entity_key,
                    )

    if difference:
        assert simulation is not None and baseline_simulation is not None
        reform_data_frame = simulation.create_data_frame_by_entity(
            values, period = period, index = False
            )[entity_key].fillna(missing_variable_default_value)
        baseline_data_frame = baseline_simulation.create_data_frame_by_entity(
            values, period = period, index = False
            )[entity_key].fillna(missing_variable_default_value)
        for value_variable in values:
            if value_variable not in baseline_data_frame:
                baseline_data_frame[value_variable] = missing_variable_default_value
            if value_variable not in reform_data_frame:
                reform_data_frame[value_variable] = missing_variable_default_value

        data_frame = reform_data_frame - baseline_data_frame

    else:
        if values:
            data_frame = (
                simulation.create_data_frame_by_entity(
                    values, period = period, index = False)[entity_key]
                )
            for value_variable in values:
                if value_variable not in data_frame:
                    data_frame[value_variable] = missing_variable_default_value
        else:
            data_frame = None

    use_baseline_data = difference or use_baseline_for_columns

    # use baseline if explicited or when computing difference
    if use_baseline_data:
        baseline_vars_data_frame = baseline_simulation.create_data_frame_by_entity(
            variables = variables,
            period = period,
            index = False
            )[entity_key]
    else:
        baseline_vars_data_frame = simulation.create_data_frame_by_entity(
            variables = variables,
            period = period,
            index = False
            )[entity_key]

    for expression in expressions:
        baseline_vars_data_frame[expression] = baseline_vars_data_frame.eval(expression)
    if filter_by is not None:
        filter_dummy = baseline_vars_data_frame[filter_by]
    if weight_variable is None:
        weight_variable = 'weight'
        baseline_vars_data_frame[weight_variable] = uniform_weight
    baseline_vars_data_frame[weight_variable] = baseline_vars_data_frame[weight_variable] * filter_dummy
    # We drop variables that are in values from baseline_vars_data_frame
    dropped_columns = [
        column for column in baseline_vars_data_frame.columns if column in values
        ]
    baseline_vars_data_frame.drop(columns = dropped_columns, inplace = True)

    data_frame = pd.concat(
        [baseline_vars_data_frame, data_frame],
        axis = 1,
        )

    if values:
        data_frame_by_value = dict()
        for value in values:
            if aggfunc in ['mean', 'sum', 'sum_abs', 'count']:
                data_frame[value] = (
                    data_frame[value] * data_frame[weight_variable]
                    if aggfunc != 'sum_abs'
                    else data_frame[value].abs() * data_frame[weight_variable]
                    )
                data_frame[value].fillna(missing_variable_default_value, inplace = True)
                pivot_sum = data_frame.pivot_table(index = index, columns = columns, values = value, aggfunc = 'sum')
                pivot_mass = data_frame.pivot_table(index = index, columns = columns, values = weight_variable, aggfunc = 'sum')
                if aggfunc == 'mean':
                    try:  # Deal with a pivot_table pandas bug https://github.com/pandas-dev/pandas/issues/17038
                        result = (pivot_sum / pivot_mass.loc[weight_variable])
                    except KeyError:
                        result = (pivot_sum / pivot_mass)
                elif aggfunc in ['sum', 'sum_abs']:
                    result = pivot_sum
                elif aggfunc == 'count':
                    result = pivot_mass.rename(columns = {weight_variable: value}, index = {weight_variable: value})

            elif aggfunc in ["min", "max"]:
                data_frame[value].fillna(missing_variable_default_value, inplace = True)
                result = data_frame.pivot_table(index = index, columns = columns, values = value, aggfunc = aggfunc)

            data_frame_by_value[value] = result

        if len(list(data_frame_by_value.keys())) > 1:
            if concat_axis is None:
                return data_frame_by_value
            else:
                assert concat_axis in [0, 1]
                return pd.concat(data_frame_by_value.values(), axis = concat_axis)
        else:
            return next(iter(data_frame_by_value.values()))

    else:
        assert aggfunc == 'count', "Can only use count for aggfunc if no values"
        return data_frame.pivot_table(index = index, columns = columns, values = weight_variable, aggfunc = 'sum')


def create_data_frame_by_entity(simulation: Simulation, variables: Optional[List] = None, expressions: Optional[List[str]] = None,
        filter_by = None, index: bool = False, period: Optional[Union[int, str, Period]] = None,
        merge: bool = False) -> Union[pd.DataFrame, Dict]:
    """
    Create dataframe(s) of variables for the whole selected population.

    Args:
        simulation (Simulation): Simulation to use.
        variables (Optional[List], optional): Variables to retrieve, None means all. Defaults to None.
        expressions (Optional[List[str]], optional): _description_. Defaults to None.
        filter_by (str, optional): Filter variable or expression to use. Defaults to None.
        index (bool, optional): Whether to use index (id) variables. Defaults to False.
        period (Optional[Union[int, str, Period]], optional): Period of the computation. Defaults to None.
        merge (bool, optional): Wheter to merge the datafrales into one. Defaults to False.

    Returns:
        pd.DataFrame of Dict: Dataframe(s) with the variables values
    """
    assert simulation is not None
    id_variable_by_entity_key = simulation.id_variable_by_entity_key
    tax_benefit_system = simulation.tax_benefit_system
    assert tax_benefit_system is not None

    if period is None:
        period = simulation.period

    assert variables or index or expressions or filter_by

    if merge:
        index = True
    if expressions is None:
        expressions = []

    if filter_by is not None:
        if filter_by in tax_benefit_system.variables:
            variables.append(filter_by)
            filter_entity_key = tax_benefit_system.variables.get(filter_by).entity.key
        else:
            filter_entity_key = assert_variables_in_same_entity(tax_benefit_system, get_words(filter_by))
            expressions.append(filter_by)

    expressions_by_entity_key = dict()
    for expression in expressions:
        expression_variables = get_words(expression)
        entity_key = assert_variables_in_same_entity(tax_benefit_system, expression_variables)
        if entity_key in expressions_by_entity_key:
            expressions_by_entity_key[entity_key].append(expression)
        else:
            expressions_by_entity_key[entity_key] = [expression]
        variables += expression_variables

    variables = set(variables)

    missing_variables = set(variables).difference(set(tax_benefit_system.variables.keys()))
    if missing_variables:
        log.info("These variables aren't part of the tax-benefit system: {}".format(missing_variables))
        log.info("These variables are ignored: {}".format(missing_variables))

    columns_to_fetch = [
        tax_benefit_system.variables.get(variable_name) for variable_name in variables
        if tax_benefit_system.variables.get(variable_name) is not None
        ]

    assert len(columns_to_fetch) >= 1, "None of the requested variables {} are in the tax-benefit-system {}".format(
        variables, list(tax_benefit_system.variables.keys()))

    assert simulation is not None

    openfisca_data_frame_by_entity_key = dict()
    non_person_entities = list()

    for entity in tax_benefit_system.entities:
        entity_key = entity.key
        column_names = [
            column.name for column in columns_to_fetch
            if column.entity.key == entity_key
            ]
        openfisca_data_frame_by_entity_key[entity_key] = pd.DataFrame(
            dict(
                (column_name, simulation.adaptative_calculate_variable(column_name, period = period))
                for column_name in column_names
                )
            )
        if entity.is_person:
            person_entity = entity
        else:
            non_person_entities.append(entity)

    if index:
        person_data_frame = openfisca_data_frame_by_entity_key.get(person_entity.key)
        person_data_frame.index.name = id_variable_by_entity_key.get("person", "person_id")
        if person_data_frame is None:
            person_data_frame = pd.DataFrame()
        for entity in non_person_entities:
            entity_key_id = id_variable_by_entity_key[entity.key]
            person_data_frame[
                entity_key_id
                ] = simulation.populations[entity.key].members_entity_id
            flattened_roles = entity.flattened_roles
            index_by_role = dict(
                (flattened_roles[index], index)
                for index in range(len(flattened_roles))
                )
            person_data_frame[
                "{}_{}".format(entity.key, 'role')
                ] = pd.Series(simulation.populations[entity.key].members_role).map(index_by_role)
            person_data_frame[
                "{}_{}".format(entity.key, 'position')
                ] = simulation.populations[entity.key].members_position

            # Set index names as entity_id
            openfisca_data_frame_by_entity_key[entity.key].index.name = entity_key_id
            openfisca_data_frame_by_entity_key[entity.key].reset_index(inplace=True)
        person_data_frame.reset_index(inplace=True)

    for entity_key, expressions in expressions_by_entity_key.items():
        data_frame = openfisca_data_frame_by_entity_key[entity_key]
        for expression in expressions:
            data_frame[expression] = data_frame.eval(expression)

    if filter_by is not None:
        openfisca_data_frame_by_entity_key[filter_entity_key] = (
            openfisca_data_frame_by_entity_key[filter_entity_key].loc[
                openfisca_data_frame_by_entity_key[filter_entity_key][filter_by]
                ].copy()
            )

    if not merge:
        return openfisca_data_frame_by_entity_key
    else:
        for entity_key, openfisca_data_frame in openfisca_data_frame_by_entity_key.items():
            if entity_key != person_entity.key:
                entity_key_id = id_variable_by_entity_key[entity_key]
                if len(openfisca_data_frame) > 0:
                    person_data_frame = person_data_frame.merge(
                        openfisca_data_frame.reset_index(),
                        left_on = entity_key_id,
                        right_on = entity_key_id,
                        )
        return person_data_frame


class SecretViolationError(Exception):
    """Raised if the result of the simulation do not comform with regulators rules."""

    pass


def compute_winners_loosers(
        simulation: Simulation,
        baseline_simulation: Simulation,
        variable: str,
        filter_by: Optional[str] = None,
        period: Optional[Union[int, str, Period]] = None,
        absolute_minimal_detected_variation: float = 0,
        relative_minimal_detected_variation: float = .01,
        observations_threshold: int = None,
        weighted: bool = True,
        alternative_weights = None,
        filtering_variable_by_entity = None,
        ) -> Dict[str, int]:
    """
    Compute the number of winners and loosers for a given variable.

    Args:
        simulation (_type_): The main simulation.
        baseline_simulation (_type_): The baseline simulation
        variable (str): The variable to use.
        filter_by (str, optional): The variable or expression to be used as a filter. Defaults to None.
        period (Optional[Union[int, str, Period]], optional): The period of the simulation. Defaults to None.
        absolute_minimal_detected_variation (float, optional): Absolute minimal variation to be detected, in ratio. Ie 0.5 means 5% of variation wont be counted..
        relative_minimal_detected_variation (float, optional): Relative minimal variation to be detected, in ratio. Defaults to .01.
        observations_threshold (int, optional): Number of observations needed to avoid a statistical secret violation. Defaults to None.
        weighted (bool, optional): Whether to use weights. Defaults to True.
        alternative_weights (Optional[Union[str, int, float, Array]], optional): Alternative weigh to use. Defaults to None.
        filtering_variable_by_entity (_type_, optional): The variable to be used as a filter for each entity. Defaults to None.

    Raises:
        SecretViolationError: Raised when statistical secret is violated.

    Returns:
        Dict[str, int]: Statistics about winners and loosers between the main simulation and the baseline.
    """
    weight_variable_by_entity = simulation.weight_variable_by_entity
    entity_key = baseline_simulation.tax_benefit_system.variables[variable].entity.key

    # Get the results of the simulation
    after = simulation.adaptative_calculate_variable(variable, period = period)
    before = baseline_simulation.adaptative_calculate_variable(variable, period = period)

    # Filter if needed
    if filtering_variable_by_entity is not None:
        if filter_by is None:
            filter_by = filtering_variable_by_entity.get(entity_key)

    if filter_by is not None:
        filter_entity_key = baseline_simulation.tax_benefit_system.variables.get(filter_by).entity.key
        assert filter_entity_key == entity_key
        filter_dummy = baseline_simulation.calculate(filter_by, period = period).astype(bool)

        after = after[filter_dummy].copy()
        before = before[filter_dummy].copy()

    # Define weights
    weight = np.ones(len(after))
    if weighted:
        if alternative_weights is not None:
            weight = alternative_weights
        elif weight_variable_by_entity is not None:
            weight_variable = weight_variable_by_entity[entity_key]
            weight = baseline_simulation.calculate(weight_variable, period = period)
        else:
            log.warn('There is no weight variable for entity {} nor alternative weights. Switch to unweighted'.format(entity_key))

    # Compute the weigthed number of zeros or non zeros
    value_by_simulation = dict(after = after, before = before)
    stats_by_simulation = dict()
    for simulation_prefix, value in value_by_simulation.items():
        stats = dict()
        stats["count_zero"] = (
            weight.astype("float64")
            * (
                (absolute_minimal_detected_variation > np.abs(value))
                )
            ).sum()
        stats["count_non_zero"] = sum(weight.astype("float64")) - stats["count_zero"]
        stats_by_simulation[simulation_prefix] = stats
        del stats

    # Compute the number of entity above or below after
    after_value = after
    before_value = before
    with np.errstate(divide="ignore", invalid="ignore"):
        above_after = ((after_value - before_value) / np.abs(before_value)) > relative_minimal_detected_variation
    almost_zero_before = np.abs(before_value) < absolute_minimal_detected_variation
    above_after[almost_zero_before * (after_value >= 0)] = (
        after_value >= absolute_minimal_detected_variation
        )[almost_zero_before * (after_value >= 0)]
    with np.errstate(divide="ignore", invalid="ignore"):
        below_after = ((after_value - before_value) / np.abs(before_value)) < -relative_minimal_detected_variation
    below_after[almost_zero_before * (after_value < 0)] = (
        after_value < -absolute_minimal_detected_variation
        )[almost_zero_before * (after_value < 0)]

    # Check if there is a secret violation, without weights
    if observations_threshold is not None:
        not_legit_below = (below_after.sum() < observations_threshold) & (below_after.sum() > 0)
        not_legit_above = (above_after.sum() < observations_threshold) & (above_after.sum() > 0)
        if not_legit_below | not_legit_above:
            raise SecretViolationError("Not enough observations involved")

    # Apply weights
    above_after_count = (above_after.astype("float64") * weight.astype("float64")).sum()
    below_after_count = (below_after.astype("float64") * weight.astype("float64")).sum()
    total = sum(weight)
    neutral = total - above_after_count - below_after_count

    return {
        "total": total,
        "non_zero_before": stats_by_simulation["before"]["count_non_zero"],
        "non_zero_after": stats_by_simulation["after"]["count_non_zero"],
        "above_after": above_after_count,
        "lower_after": below_after_count,
        "neutral": neutral,
        "tolerance_factor_used": relative_minimal_detected_variation,
        "weight_factor": 1,
        }


def init_entity_data(simulation: Simulation, entity: Entity, filtered_input_data_frame: pd.DataFrame, period: Period,
        used_as_input_variables_by_entity: Dict):
    """
    Initialize entity in simulation at some period with input provided by a dataframe.

    Args:
        simulation (Simulation): The simulation to initialize.
        entity (Entity): The entity which variables to initialize.
        filtered_input_data_frame (pd.DataFrame): The dataframe with the variables values.
        period (Period): The period to initialize.
        used_as_input_variables_by_entity (Dict): The variable to be used to initialize each entity.
    """
    used_as_input_variables = used_as_input_variables_by_entity[entity.key]
    input_data_frame = filtered_input_data_frame
    # input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame)
    diagnose_variable_mismatch(used_as_input_variables, input_data_frame)

    for column_name, column_serie in input_data_frame.items():
        variable_instance = simulation.tax_benefit_system.variables.get(column_name)
        if variable_instance is None:
            log.info(f"Ignoring {column_name} in input data")
            continue

        if variable_instance.entity.key != entity.key:
            log.info("Ignoring variable {} which is not part of entity {} but {}".format(
                column_name, entity.key, variable_instance.entity.key))
            continue
        init_variable_in_entity(simulation, entity.key, column_name, column_serie, period)


def inflate(simulation: Simulation, inflator_by_variable: Optional[Dict] = None, period: Optional[Union[int, str, Period]] = None,
        target_by_variable: Optional[Dict] = None):
    tax_benefit_system = simulation.tax_benefit_system
    for variable_name in set(inflator_by_variable.keys()).union(set(target_by_variable.keys())):
        assert variable_name in tax_benefit_system.variables, \
            "Variable {} is not a valid variable of the tax-benefit system".format(variable_name)
        if variable_name in target_by_variable:
            inflator = inflator_by_variable[variable_name] = \
                target_by_variable[variable_name] / simulation.compute_aggregate(
                    variable = variable_name, period = period)
            log.info('Using {} as inflator for {} to reach the target {} '.format(
                inflator, variable_name, target_by_variable[variable_name]))
        else:
            assert variable_name in inflator_by_variable, 'variable_name is not in inflator_by_variable'
            log.info('Using inflator {} for {}.  The target is thus {}'.format(
                inflator_by_variable[variable_name],
                variable_name, inflator_by_variable[variable_name] * simulation.compute_aggregate(
                    variable = variable_name, period = period)
                ))
            inflator = inflator_by_variable[variable_name]

        array = simulation.calculate_add(variable_name, period = period)
        assert array is not None
        simulation.delete_arrays(variable_name, period = period)  # delete existing arrays
        simulation.set_input(variable_name, period, inflator * array)  # insert inflated array


def _load_table_for_survey(config_files_directory, collection, survey, table, batch_size=None, batch_index=None, filter_by=None):
    if survey is not None:
        input_data_frame = load_table(config_files_directory = config_files_directory, collection = collection, survey = survey,
            table = table, batch_size=batch_size, batch_index=batch_index, filter_by=filter_by)
    else:
        input_data_frame = load_table(config_files_directory = config_files_directory, collection = collection, survey = 'input',
            table = table, batch_size=batch_size, batch_index=batch_index, filter_by=filter_by)
    return input_data_frame


def _input_data_table_by_entity_by_period_monolithic(tax_benefit_system, simulation, period, input_data_table_by_entity, builder, custom_input_data_frame, config_files_directory, collection, survey = None):
    """
    Initialize simulation with input data from a table for each entity and period.
    """
    period = periods.period(period)
    simulation_datasets = {}
    entities = tax_benefit_system.entities
    for entity in entities:
        # Read all tables for the entity
        log.debug(f"init_simulation - {period=} {entity.key=}")
        table = input_data_table_by_entity.get(entity.key)
        filter_by = input_data_table_by_entity.get('filter_by', None)
        if table is None:
            continue
        input_data_frame = _load_table_for_survey(config_files_directory, collection, survey, table, filter_by = filter_by)
        simulation_datasets[entity.key] = input_data_frame

    if simulation is None:
        # Instantiate simulation only for the fist period
        # Next period will reuse the same simulation
        for entity in entities:
            table = input_data_table_by_entity.get(entity.key)
            if table is None:
                continue
            custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
            builder.init_entity_structure(entity, simulation_datasets[entity.key])  # TODO complete args
        simulation = builder.build(tax_benefit_system)
        simulation.id_variable_by_entity_key = builder.id_variable_by_entity_key  # Should be propagated to enhanced build

    for entity in entities:
        # Load data in the simulation
        table = input_data_table_by_entity.get(entity.key)
        if table is None:
            continue
        log.debug(f"init_simulation - {entity.key=} {len(input_data_frame)=}")
        simulation.init_entity_data(entity, simulation_datasets[entity.key], period, builder.used_as_input_variables_by_entity)
        del simulation_datasets[entity.key]
    return simulation


def _input_data_table_by_entity_by_period_batch(tax_benefit_system, simulation, period, input_data_table_by_entity, builder, custom_input_data_frame, config_files_directory, collection, survey = None):
    """
    Initialize simulation with input data from a table for each entity and period.
    """
    period = periods.period(period)
    batch_size = input_data_table_by_entity.get('batch_size')
    batch_index = input_data_table_by_entity.get('batch_index', 0)
    batch_entity = input_data_table_by_entity.get('batch_entity')
    batch_entity_key = input_data_table_by_entity.get('batch_entity_key')
    filtered_entity = input_data_table_by_entity.get('filtered_entity')
    filtered_entity_on_key = input_data_table_by_entity.get('filtered_entity_on_key')
    if not batch_entity or not batch_entity_key or not filtered_entity or not filtered_entity_on_key:
        raise ValueError("batch_entity, batch_entity_key, filtered_entity and filtered_entity_on_key are required")
    simulation_datasets = {
        batch_entity: {
            'table_key': batch_entity_key,
            'input_data_frame': None,
            'entity': None,
            },
        filtered_entity: {
            'table_key': filtered_entity_on_key,
            'input_data_frame': None,
            'entity': None,
            }
        }
    batch_entity_ids = None
    entities = tax_benefit_system.entities

    if len(entities) > 2:
        # Batch mode could work only with batch_entity and filtered_entity, and no others
        warnings.warn(f"survey-manager.simulation._input_data_table_by_entity_by_period_batch : Your TaxBenefitSystem has {len(entities)} entities but we will only load  {batch_entity} and {filtered_entity}.", stacklevel=2)

    for entity_name, entity_data in simulation_datasets.items():
        # Find Identity object from TaxBenefitSystem
        for entity in entities:
            if entity.key == entity_name:
                entity_data['entity'] = entity
                break

    # Load the batch entity
    table = input_data_table_by_entity[batch_entity]
    input_data_frame = _load_table_for_survey(config_files_directory, collection, survey, table, batch_size, batch_index)
    batch_entity_ids = input_data_frame[batch_entity_key].to_list()
    simulation_datasets[batch_entity]['input_data_frame'] = input_data_frame

    # Load the filtered entity
    table = input_data_table_by_entity[filtered_entity]
    filter_by = [(filtered_entity_on_key, 'in', batch_entity_ids)]
    input_data_frame = _load_table_for_survey(config_files_directory, collection, survey, table, filter_by = filter_by)
    simulation_datasets[filtered_entity]['input_data_frame'] = input_data_frame

    if simulation is None:
        for entity_name, entity_data in simulation_datasets.items():
            custom_input_data_frame(entity_data['input_data_frame'], period = period, entity = entity_name)
            builder.init_entity_structure(entity_data['entity'], entity_data['input_data_frame'])
        simulation = builder.build(tax_benefit_system)
        simulation.id_variable_by_entity_key = builder.id_variable_by_entity_key  # Should be propagated to enhanced build
    for _entity_name, entity_data in simulation_datasets.items():
        simulation.init_entity_data(entity_data['entity'], entity_data['input_data_frame'], period, builder.used_as_input_variables_by_entity)
    return simulation


def init_simulation(tax_benefit_system, period, data):
    builder = SimulationBuilder()
    builder.create_entities(tax_benefit_system)

    collection = data.get("collection")
    custom_input_data_frame = data.get("custom_input_data_frame", do_nothing)
    data_year = data.get("data_year")
    survey = data.get('survey')
    config_files_directory = data.get("config_files_directory")
    builder.used_as_input_variables = data.get("used_as_input_variables")
    builder.id_variable_by_entity_key = data.get("id_variable_by_entity_key")
    builder.role_variable_by_entity_key = data.get("role_variable_by_entity_key")
    builder.tax_benefit_system = tax_benefit_system

    default_source_types = [
        'input_data_frame',
        'input_data_table',
        'input_data_frame_by_entity',
        'input_data_frame_by_entity_by_period',
        'input_data_table_by_entity_by_period',
        'input_data_table_by_period',
        ]
    source_types = [
        source_type_
        for source_type_ in default_source_types
        if data.get(source_type_, None) is not None
        ]
    assert len(source_types) < 2, "There are too many data source types"
    assert len(source_types) >= 1, "There should be one data source type included in {}".format(
        default_source_types)
    source_type = source_types[0]
    source = data[source_type]

    if source_type == 'input_data_frame_by_entity':
        assert data_year is not None
        source_type = 'input_data_frame_by_entity_by_period'
        source = {periods.period(data_year): source}

    input_data_survey_prefix = data.get("input_data_survey_prefix") if data is not None else None

    if source_type == 'input_data_frame':
        simulation = builder.init_all_entities(source, period)

    if source_type == 'input_data_table':
        # Case 1: fill simulation with a unique input_data_frame given by the attribute
        if input_data_survey_prefix is not None:
            openfisca_survey_collection = SurveyCollection.load(collection = collection)
            openfisca_survey = openfisca_survey_collection.get_survey("{}_{}".format(
                input_data_survey_prefix, data_year))
            input_data_frame = openfisca_survey.get_values(table = "input").reset_index(drop = True)
        else:
            NotImplementedError

        custom_input_data_frame(input_data_frame, period = period)
        simulation = builder.init_all_entities(input_data_frame, builder, period)  # monolithic dataframes

    elif source_type == 'input_data_table_by_period':
        # Case 2: fill simulation with input_data_frame by period containing all entity variables
        input_data_table_by_period = data.get("input_data_table_by_period")
        for period, table in input_data_table_by_period.items():
            period = periods.period(period)
            log.debug('From survey {} loading table {}'.format(survey, table))
            input_data_frame = load_table(config_files_directory = config_files_directory, collection = collection, survey = survey, input_data_survey_prefix = input_data_survey_prefix, table = table)
            custom_input_data_frame(input_data_frame, period = period)
            simulation = builder.init_all_entities(input_data_frame, builder, period)  # monolithic dataframes

    elif source_type == 'input_data_frame_by_entity_by_period':
        for period, input_data_frame_by_entity in source.items():
            period = periods.period(period)
            for entity in tax_benefit_system.entities:
                input_data_frame = input_data_frame_by_entity.get(entity.key)
                if input_data_frame is None:
                    continue
                custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                builder.init_entity_structure(entity, input_data_frame)  # TODO complete args

        simulation = builder.build(tax_benefit_system)
        simulation.id_variable_by_entity_key = builder.id_variable_by_entity_key  # Should be propagated to enhanced build

        for period, input_data_frame_by_entity in source.items():
            for entity in tax_benefit_system.entities:
                input_data_frame = input_data_frame_by_entity.get(entity.key)
                if input_data_frame is None:
                    log.debug("No input_data_frame found for entity {} at period {}".format(entity, period))
                    continue
                custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                simulation.init_entity_data(entity, input_data_frame, period, builder.used_as_input_variables_by_entity)

    elif source_type == 'input_data_table_by_entity_by_period':
        # Case 3: fill simulation with input_data_table by entity_by_period containing a dictionnary
        # of all periods containing a dictionnary of entity variables
        input_data_table_by_entity_by_period = source
        simulation = None
        for period, input_data_table_by_entity in input_data_table_by_entity_by_period.items():
            if input_data_table_by_entity.get('batch_size'):
                simulation = _input_data_table_by_entity_by_period_batch(tax_benefit_system, simulation, period, input_data_table_by_entity, builder, custom_input_data_frame, config_files_directory, collection, survey)
            else:
                simulation = _input_data_table_by_entity_by_period_monolithic(tax_benefit_system, simulation, period, input_data_table_by_entity, builder, custom_input_data_frame, config_files_directory, collection, survey)

    else:
        pass

    if data_year is not None:
        simulation.period = periods.period(data_year)

    return simulation


def init_variable_in_entity(simulation: Simulation, entity, variable_name, series, period):
    variable = simulation.tax_benefit_system.variables[variable_name]

    # np.issubdtype cannot handles categorical variables
    if (not isinstance(series, pd.CategoricalDtype)) and np.issubdtype(series.values.dtype, np.floating):
        if series.isnull().any():
            log.debug('There are {} NaN values for {} non NaN values in variable {}'.format(
                series.isnull().sum(), series.notnull().sum(), variable_name))
            log.debug('We convert these NaN values of variable {} to {} its default value'.format(
                variable_name, variable.default_value))
            series.fillna(variable.default_value, inplace = True)
        assert series.notnull().all(), \
            'There are {} NaN values for {} non NaN values in variable {}'.format(
                series.isnull().sum(), series.notnull().sum(), variable_name)

    enum_variable_imputed_as_enum = (
        variable.value_type == Enum
        and (
            isinstance(series, pd.CategoricalDtype)
            or not (
                np.issubdtype(series.values.dtype, np.integer)
                or np.issubdtype(series.values.dtype, float)
                )
            )
        )

    if enum_variable_imputed_as_enum:
        if series.isnull().any():
            log.debug('There are {} NaN values ({}% of the array) in variable {}'.format(
                series.isnull().sum(), series.isnull().mean() * 100, variable_name))
            log.debug('We convert these NaN values of variable {} to {} its default value'.format(
                variable_name, variable.default_value._name_))
            series.fillna(variable.default_value._name_, inplace = True)
        possible_values = variable.possible_values
        index_by_category = dict(zip(
            possible_values._member_names_,
            range(len(possible_values._member_names_))
            ))
        series.replace(index_by_category, inplace = True)

    if series.values.dtype != variable.dtype:
        log.debug(
            'Converting {} from dtype {} to {}'.format(
                variable_name, series.values.dtype, variable.dtype)
            )

    array = series.values.astype(variable.dtype)
    np_array = np.array(array, dtype = variable.dtype)

    if (variable.value_type == Enum) and (np.issubdtype(series.values.dtype, np.integer) or np.issubdtype(series.values.dtype, float)):
        np_array = EnumArray(np_array, variable.possible_values)

    if variable.definition_period == YEAR and period.unit == MONTH:
        # Some variables defined for a year are present in month/quarter dataframes
        # Cleaning the dataframe would probably be better in the long run
        log.warn(f"Trying to set a monthly value for variable {variable_name}, which is defined on a year. The  montly values you provided will be summed.")

        if simulation.get_array(variable_name, period.this_year) is not None:
            array_sum = simulation.get_array(variable_name, period.this_year) + np_array
            simulation.set_input(variable_name, period.this_year, array_sum)
        else:
            simulation.set_input(variable_name, period.this_year, np_array)

    else:
        simulation.set_input(variable_name, period, np_array)


def new_from_tax_benefit_system(
        tax_benefit_system: TaxBenefitSystem,
        debug: bool = False,
        trace: bool = False,
        data: Dict = None,
        memory_config: MemoryConfig = None,
        period: Optional[Union[int, str, Period]] = None,
        custom_initialize: Callable = None,
        ) -> Simulation:
    """
    Create and initialize a simulation from a tax and benefit system and data.

    Args:
        tax_benefit_system (TaxBenefitSystem): The tax and benefit system
        debug (bool, optional): Whether to activate debugging. Defaults to False.
        trace (bool, optional): Whether to activate tracing. Defaults to False.
        data (Dict, optional): The information about data. Defaults to None.
        memory_config (MemoryConfig, optional): The memory handling config. Defaults to None.
        period (Optional[Union[int, str, Period]], optional): The period of the simulation. Defaults to None.
        custom_initialize (Callable, optional): The post-processing initialization function. Defaults to None.

    Returns:
        Simulation: The completely initialized function
    """

    simulation = Simulation.init_simulation(tax_benefit_system, period, data)
    simulation.debug = debug
    simulation.trace = trace
    simulation.opt_out_cache = True if simulation.tax_benefit_system.cache_blacklist is not None else False
    simulation.memory_config = memory_config

    if custom_initialize:
        custom_initialize(simulation)

    return simulation


def print_memory_usage(simulation: Simulation):
    """
    Print memory usage.

    Args:
        simulation (Simulation): The simulation which memory usage is to be printed
    """
    memory_usage_by_variable = simulation.get_memory_usage()['by_variable']
    try:
        usage_stats = simulation.tracer.usage_stats
    except AttributeError:
        log.warning("The simulation trace mode is not activated. You need to activate it to get stats about variable usage (hits).")
        usage_stats = None
    infos_lines = list()

    for variable, infos in memory_usage_by_variable.items():
        hits = usage_stats[variable]['nb_requests'] if usage_stats else None
        infos_lines.append((
            infos['total_nb_bytes'],
            variable, "{}: {} periods * {} cells * item size {} ({}) = {} with {} hits".format(
                variable,
                infos['nb_arrays'],
                infos['nb_cells_by_array'],
                infos['cell_size'],
                infos['dtype'],
                humanize.naturalsize(infos['total_nb_bytes'], gnu = True),
                hits,
                )
            ))
    infos_lines.sort()
    for _, _, line in infos_lines:
        print(line.rjust(100))  # noqa analysis:ignore


def set_weight_variable_by_entity(
        simulation: Simulation,
        weight_variable_by_entity: Dict,
        ):
    """
    Set weight variable for each entity.

    Args:
        simulation (Simulation): The simulation concerned.
        weight_variable_by_entity (Dict): The weight variable for each entity.
    """
    simulation.weight_variable_by_entity = weight_variable_by_entity


def summarize_variable(simulation: Simulation, variable = None, weighted = False, force_compute = False):
    """Print a summary of a variable including its memory usage.

    Args:
        variable(string): The variable being summarized
        use_baseline(bool): The tax-benefit-system considered
        weighted(bool): Whether the produced statistics should be weigthted or not
        force_compute(bool): Whether the computation of the variable should be forced

    # Example:
    #     >>> from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
    #     >>> survey_scenario = create_randomly_initialized_survey_scenario()
    #     >>> survey_scenario.summarize_variable(variable = "housing_occupancy_status", force_compute = True)
    #     <BLANKLINE>
    #     housing_occupancy_status: 1 periods * 5 cells * item size 2 (int16, default = HousingOccupancyStatus.tenant) = 10B
    #     Details:
    #     2017-01: owner = 0.00e+00 (0.0%), tenant = 5.00e+00 (100.0%), free_lodger = 0.00e+00 (0.0%), homeless = 0.00e+00 (0.0%).
    #     >>> survey_scenario.summarize_variable(variable = "rent", force_compute = True)
    #     <BLANKLINE>
    #     rent: 2 periods * 5 cells * item size 4 (float32, default = 0) = 40B
    #     Details:
    #     2017-01: mean = 562.385107421875, min = 156.01864624023438, max = 950.7142944335938, mass = 2.81e+03, default = 0.0%, median = 598.6585083007812
    #     2018-01: mean = 562.385107421875, min = 156.01864624023438, max = 950.7142944335938, mass = 2.81e+03, default = 0.0%, median = 598.6585083007812
    #     >>> survey_scenario.tax_benefit_system.neutralize_variable('age')
    #     >>> survey_scenario.summarize_variable(variable = "age")
    #     <BLANKLINE>
    #     age: neutralized variable (int64, default = 0)
    """
    tax_benefit_system = simulation.tax_benefit_system
    variable_instance = tax_benefit_system.variables.get(variable)
    assert variable_instance is not None, "{} is not a valid variable".format(variable)

    default_value = variable_instance.default_value
    value_type = variable_instance.value_type

    if variable_instance.is_neutralized:
        print("")  # noqa analysis:ignore
        print("{}: neutralized variable ({}, default = {})".format(variable, str(np.dtype(value_type)), default_value))  # noqa analysis:ignore
        return

    if weighted:
        weight_variable = simulation.weight_variable_by_entity[variable_instance.entity.key]
        weights = simulation.calculate(weight_variable, simulation.period)

    infos = simulation.get_memory_usage(variables = [variable])['by_variable'].get(variable)
    if not infos:
        if force_compute:
            simulation.adaptative_calculate_variable(variable = variable, period = simulation.period)
            simulation.summarize_variable(variable = variable, weighted = weighted)
            return
        else:
            print("{} is not computed yet. Use keyword argument force_compute = True".format(variable))  # noqa analysis:ignore
            return

    header_line = "{}: {} periods * {} cells * item size {} ({}, default = {}) = {}".format(
        variable,
        infos['nb_arrays'],
        infos['nb_cells_by_array'],
        infos['cell_size'],
        str(np.dtype(infos['dtype'])),
        default_value,
        humanize.naturalsize(infos['total_nb_bytes'], gnu = True),
        )
    print("")  # noqa analysis:ignore
    print(header_line)  # noqa analysis:ignore
    print("Details:")  # noqa analysis:ignore
    holder = simulation.get_holder(variable)
    if holder is not None:
        if holder.variable.definition_period == ETERNITY:
            array = holder.get_array(ETERNITY)
            print("permanent: mean = {}, min = {}, max = {}, median = {}, default = {:.1%}".format(  # noqa analysis:ignore
                # Need to use float to avoid hit the int16/int32 limit. np.average handles it without conversion
                array.astype(float).mean() if not weighted else np.average(array, weights = weights),
                array.min(),
                array.max(),
                np.median(array.astype(float)),
                (
                    (array == default_value).sum() / len(array)
                    if not weighted
                    else ((array == default_value) * weights).sum() / weights.sum()
                    )
                ))
        else:
            for period in sorted(simulation.get_known_periods(variable)):
                array = holder.get_array(period)
                if array.shape == ():
                    print("{}: always = {}".format(period, array))  # noqa analysis:ignore
                    continue

                if value_type == Enum:
                    possible_values = variable_instance.possible_values
                    categories_by_index = dict(zip(
                        range(len(possible_values._member_names_)),
                        possible_values._member_names_
                        ))
                    categories_type = pd.api.types.CategoricalDtype(categories = possible_values._member_names_, ordered = True)
                    df = pd.DataFrame({variable: array}).replace(categories_by_index).astype(categories_type)
                    df['weights'] = weights if weighted else 1
                    groupby = df.groupby(variable)['weights'].sum()
                    total = groupby.sum()
                    expr = [" {} = {:.2e} ({:.1%})".format(index, row, row / total) for index, row in groupby.items()]
                    print("{}:{}.".format(period, ",".join(expr)))  # noqa analysis:ignore
                    continue

                print("{}: mean = {}, min = {}, max = {}, mass = {:.2e}, default = {:.1%}, median = {}".format(  # noqa analysis:ignore
                    period,
                    array.astype(float).mean() if not weighted else np.average(array, weights = weights),
                    array.min(),
                    array.max(),
                    array.astype(float).sum() if not weighted else np.sum(array * weights),
                    (
                        (array == default_value).sum() / len(array)
                        if not weighted
                        else ((array == default_value) * weights).sum() / weights.sum()
                        ),
                    np.median(array),
                    ))


# Monkey patching

Simulation.adaptative_calculate_variable = adaptative_calculate_variable
Simulation.compute_aggregate = compute_aggregate
Simulation.compute_pivot_table = compute_pivot_table
Simulation.create_data_frame_by_entity = create_data_frame_by_entity
Simulation.compute_quantiles = compute_quantiles
Simulation.compute_winners_loosers = compute_winners_loosers
Simulation.new_from_tax_benefit_system = new_from_tax_benefit_system
Simulation.inflate = inflate
Simulation.init_entity_data = init_entity_data
Simulation.init_simulation = init_simulation
Simulation.init_variable_in_entity = init_variable_in_entity
Simulation.print_memory_usage = print_memory_usage
Simulation.set_weight_variable_by_entity = set_weight_variable_by_entity
Simulation.summarize_variable = summarize_variable
