"""Monkey-patch openfisca_core.simulations.Simulation to work with pandas."""

import logging
import numpy as np
import pandas as pd
import re

from openfisca_core import periods
from openfisca_core.simulations import Simulation
from openfisca_survey_manager.statshelpers import mark_weighted_percentiles

log = logging.getLogger(__name__)


# Helpers

def assert_variables_in_same_entity(tax_benefit_system, variables):
    """Asserts taht variables are in the same entity

    Args:
      survey_scenario: Host SurveyScenario
      variables: Variables to check presence

    Returns:
      str: Unique entity key if variables all belongs to it

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


def get_words(text):
    return re.compile('[A-Za-z_]+').findall(text)


# Main functions

def adaptative_calculate_variable(simulation, variable = None, period = None):
    assert variable is not None
    assert simulation is not None
    assert period is not None

    tax_benefit_system = simulation.tax_benefit_system

    if isinstance(period, (int, np.integer)):
        period = str(period)
    if not isinstance(period, periods.Period):
        period = periods.period(period)
    assert simulation is not None
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
    assert values is not None, 'Unspecified calculation period for variable {}'.format(variable)

    return values


def compute_aggregate(simulation, variable = None, aggfunc = 'sum', filter_by = None, period = None,
        missing_variable_default_value = np.nan, weighted = True, alternative_weights = None,
        filtering_variable_by_entity = None, weight_variable_by_entity = None):

    tax_benefit_system = simulation.tax_benefit_system

    if period is None:
        period = simulation.period

    entity_key = tax_benefit_system.variables[variable].entity.key

    if filter_by is None and filtering_variable_by_entity is not None:
        filter_by_variable = filtering_variable_by_entity.get(entity_key)

    if filter_by:
        filter_by_variable = get_words(filter_by)[0]
        assert filter_by_variable in tax_benefit_system.variables, \
            "{} is not a variables of the tax benefit system".format(filter_by_variable)
        entity_key = tax_benefit_system.variables[variable].entity.key
        filter_by_entity_key = tax_benefit_system.variables[filter_by_variable].entity.key
        assert filter_by_entity_key == entity_key, \
            ("You tried to compute agregates for variable '{0}', of entity {1}"
            " filtering by variable '{2}', of entity {3}. This is not possible."
            " Please choose a filter-by variable of same entity as '{0}'."
            .format(variable, entity_key, filter_by_variable, filter_by_entity_key))

    uniform_weight = np.array(1.0)
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

            else:
                log.warn('There is no weight variable for entity {} nor alternative weights. Switch to unweighted'.format(entity_key))

    if variable in simulation.tax_benefit_system.variables:
        value = simulation.adaptative_calculate_variable(variable = variable, period = period)
    else:
        log.debug("Variable {} not found. Assiging {}".format(variable, missing_variable_default_value))
        return missing_variable_default_value

    weight = (
        simulation.adaptative_calculate_variable(variable = weight_variable, period = period).astype(float)
        if weight_variable else uniform_weight
        )
    filter_dummy = simulation.adaptative_calculate_variable(variable = filter_by_variable, period = period) if filter_by else 1.0
    if filter_by:
        filter_dummy = pd.DataFrame({'{}'.format(filter_by_variable): filter_dummy}).eval(filter_by)

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


def compute_quantiles(simulation = None, variable = None, nquantiles = None, period = None, filter_by = None,
        weighted = True, alternative_weights = None,
        filtering_variable_by_entity = None, weight_variable_by_entity = None):

    weight_variable = None
    entity_key = simulation.tax_benefit_system.variables[variable].entity.key
    if weight_variable_by_entity:
        weight_variable = weight_variable_by_entity[entity_key]

    if filter_by is not None:
        NotImplementedError("filter_by option not implemented")

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

    labels = np.arange(1, nquantiles + 1)
    method = 2
    quantile, values = mark_weighted_percentiles(variable_values, labels, weight, method, return_quantiles = True)
    del quantile
    return values


def compute_pivot_table(simulation = None, baseline_simulation = None, aggfunc = 'mean',
        columns = None, difference = False, filter_by = None, index = None,
        period = None, use_baseline_for_columns = None, values = None,
        missing_variable_default_value = np.nan, concat_axis = None, weighted = True, alternative_weights = None,
        filtering_variable_by_entity = None, weight_variable_by_entity = None):

    admissible_aggfuncs = ['max', 'mean', 'min', 'sum', 'count']
    assert aggfunc in admissible_aggfuncs

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
            if aggfunc in ['mean', 'sum', 'count']:
                data_frame[value] = data_frame[value] * data_frame[weight_variable]
                data_frame[value].fillna(missing_variable_default_value, inplace = True)
                pivot_sum = data_frame.pivot_table(index = index, columns = columns, values = value, aggfunc = 'sum')
                pivot_mass = data_frame.pivot_table(index = index, columns = columns, values = weight_variable, aggfunc = 'sum')
                if aggfunc == 'mean':
                    try:  # Deal with a pivot_table pandas bug https://github.com/pandas-dev/pandas/issues/17038
                        result = (pivot_sum / pivot_mass.loc[weight_variable])
                    except KeyError:
                        result = (pivot_sum / pivot_mass)
                elif aggfunc == 'sum':
                    result = pivot_sum
                elif aggfunc == 'count':
                    result = pivot_mass

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


def create_data_frame_by_entity(simulation, variables = None, expressions = None, filter_by = None, index = False,
        period = None, merge = False, id_variable_by_entity_key = None):

    assert simulation is not None
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
                (column_name, simulation.adaptative_calculate_variable(
                    variable = column_name, period = period))
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
                "{}_{}".format(entity.key, 'id')
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
                openfisca_data_frame.index.name = '{}_id'.format(entity_key)
                if len(openfisca_data_frame.reset_index()) > 0:
                    person_data_frame = person_data_frame.merge(
                        openfisca_data_frame.reset_index(),
                        left_on = '{}_id'.format(entity_key),
                        right_on = '{}_id'.format(entity_key),
                        )
        return person_data_frame


# Monkey patching

Simulation.adaptative_calculate_variable = adaptative_calculate_variable
Simulation.compute_aggregate = compute_aggregate
Simulation.compute_pivot_table = compute_pivot_table
Simulation.create_data_frame_by_entity = create_data_frame_by_entity
Simulation.compute_quantiles = compute_quantiles
