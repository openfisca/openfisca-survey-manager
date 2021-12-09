"""Abstract survey scenario definition."""

from typing import Dict, List


import re


import logging
import os
import numpy as np
import pandas as pd


import humanize


from openfisca_core import periods
from openfisca_core.simulation_builder import SimulationBuilder
from openfisca_core.indexed_enums import Enum
from openfisca_core.periods import MONTH, YEAR, ETERNITY
from openfisca_core.tools.simulation_dumper import dump_simulation, restore_simulation

from openfisca_survey_manager.calibration import Calibration

from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey

log = logging.getLogger(__name__)


class AbstractSurveyScenario(object):
    """Abstract survey scenario."""

    baseline_simulation = None
    baseline_tax_benefit_system = None
    cache_blacklist = None
    collection = None
    debug = False
    filtering_variable_by_entity = None
    id_variable_by_entity_key = None
    inflator_by_variable = None  # factor used to inflate variable total
    input_data_frame = None
    input_data_table_by_entity_by_period = None
    input_data_table_by_period = None
    non_neutralizable_variables = None
    role_variable_by_entity_key = None
    simulation = None
    target_by_variable = None  # variable total target to inflate to
    tax_benefit_system = None
    trace = False
    used_as_input_variables = None
    used_as_input_variables_by_entity = None
    variation_factor = .03  # factor used to compute variation when estimating marginal tax rate
    varying_variable = None
    weight_variable_by_entity = None
    year = None

    def build_input_data(self, **kwargs):
        """Build input data."""
        NotImplementedError

    def calculate_series(self, variable, period = None, use_baseline = False):
        """Compute variable values for period and baseline or reform tax benefit and system.

        Args:
          variable(str, optional): Variable to compute
          period(Period, optional): Period, defaults to None
          use_baseline(bool, optional): Use baseline tax and benefit system, defaults to False

        Returns:
          pandas.Series: Variable values

        """
        return pd.Series(
            data = self.calculate_variable(variable, period, use_baseline),
            name = variable,
            )

    def calculate_variable(self, variable, period = None, use_baseline = False):
        """Compute variable values for period and baseline or reform tax benefit and system.

        Args:
          variable(str, optional): Variable to compute
          period(Period, optional): Period, defaults to None
          use_baseline(bool, optional): Use baseline tax and benefit system, defaults to False

        Returns:
          numpy.ndarray: Variable values

        """
        if use_baseline:
            assert self.baseline_simulation is not None, "self.baseline_simulation is None"
            simulation = self.baseline_simulation
        else:
            assert self.simulation is not None
            simulation = self.simulation

        tax_benefit_system = simulation.tax_benefit_system

        assert period is not None
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

    def calibrate(self, target_margins_by_variable: dict = None, parameters: dict = None, total_population: float = None):
        """Calibrate the scenario data.

        Args:
            target_margins_by_variable (dict, optional): Variable targets margins. Defaults to None.
            parameters (dict, optional): Calibration parameters. Defaults to None.
            total_population (float, optional): Total population target. Defaults to None.
        """
        survey_scenario = self
        calibration = Calibration(survey_scenario)

        if parameters is not None:
            assert parameters['method'] in ['linear', 'raking ratio', 'logit'], \
                "Incorect parameter value: method should be 'linear', 'raking ratio' or 'logit'"
            if parameters['method'] == 'logit':
                assert parameters['invlo'] is not None
                assert parameters['up'] is not None
        else:
            parameters = dict(method = 'logit', up = 3, invlo = 3)

        calibration.parameters.update(parameters)

        if total_population:
            calibration.total_population = total_population

        if target_margins_by_variable is not None:
            calibration.set_target_margins(target_margins_by_variable)

        calibration.calibrate()
        calibration.set_calibrated_weights()
        self.calibration = calibration

    def compute_aggregate(self, variable = None, aggfunc = 'sum', filter_by = None, period = None, use_baseline = False,
            difference = False, missing_variable_default_value = np.nan, weighted = True, alternative_weights = None):
        """Compute variable aggregate.

        Args:
          variable: Variable (Default value = None)
          aggfunc: Aggregation function (Default value = 'sum')
          filter_by: Filtering variable (Default value = None)
          period: Period in which the variable is computed. If None, simulation.period is chosen (Default value = None)
          use_baseline: Use baseline simulation (Default value = False)
          difference:  Compute difference between simulation and baseline (Default value = False)
          missing_variable_default_value: Value of missing variable (Default value = np.nan)
          weighted: Whether to weight te aggregates (Default value = True)
          alternative_weights: Weight variable name or numerical value. Use SurveyScenario's weight_variable_by_entity if None, and if the latetr is None uses 1 ((Default value = None)

        Returns:
          float: Aggregate

        """
        assert aggfunc in ['count', 'mean', 'sum', 'count_non_zero']
        assert period is not None
        assert not (difference and use_baseline), "Can't have difference and use_baseline both set to True"

        if difference:
            return (
                self.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    use_baseline = False,
                    missing_variable_default_value = missing_variable_default_value,
                    weighted = weighted,
                    alternative_weights = alternative_weights,
                    )
                - self.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    use_baseline = True,
                    missing_variable_default_value = missing_variable_default_value,
                    weighted = weighted,
                    alternative_weights = alternative_weights,
                    )
                )

        tax_benefit_system = self.tax_benefit_system
        entity_key = tax_benefit_system.variables[variable].entity.key

        if filter_by is None and self.filtering_variable_by_entity is not None:
            filter_by_variable = self.filtering_variable_by_entity.get(entity_key)

        assert variable is not None
        if use_baseline:
            simulation = self.baseline_simulation
            assert simulation is not None, "Missing baseline simulation"
        else:
            simulation = self.simulation
            assert simulation is not None, "Missing (reform) simulation"

        if period is None:
            period = simulation.period

        if filter_by:
            filter_by_variable = get_words(filter_by)[0]
            assert filter_by_variable in self.tax_benefit_system.variables, \
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

                elif type(alternative_weights) == int or type(alternative_weights) == float:
                    weight_variable = None
                    uniform_weight = float(alternative_weights)

            else:
                if self.weight_variable_by_entity:
                    weight_variable = self.weight_variable_by_entity[entity_key]

                else:
                    log.warn('There is no weight variable for entity {} nor alternative weights. Switch to unweighted'.format(entity_key))

        if variable in simulation.tax_benefit_system.variables:
            value = self.calculate_variable(variable = variable, period = period, use_baseline = use_baseline)
        else:
            log.debug("Variable {} not found. Assiging {}".format(variable, missing_variable_default_value))
            return missing_variable_default_value

        weight = (
            self.calculate_variable(
                variable = weight_variable, period = period, use_baseline = use_baseline
                ).astype(float)
            if weight_variable else uniform_weight
            )
        filter_dummy = self.calculate_variable(variable = filter_by_variable, period = period) if filter_by else 1.0
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

    def compute_marginal_tax_rate(self, target_variable, period, use_baseline = False,
            value_for_zero_varying_variable = 0.0):
        """
        Compute marginal a rate of a target (MTR) with respect to a varying variable.

        Args:
            target_variable (str): the variable which marginal tax rate is computed
            period (Period): the period at which the the marginal tax rate is computed
            use_baseline (bool, optional): compute the marginal tax rate for the baseline system. Defaults to False.
            value_for_zero_varying_variable (float, optional): value of MTR when the varying variable is zero. Defaults to 0.

        Returns:
            numpy.array: Vector of marginal rates
        """
        varying_variable = self.varying_variable
        if use_baseline:
            simulation = self.baseline_simulation
            assert self._modified_baseline_simulation is not None
            modified_simulation = self._modified_baseline_simulation
        else:
            assert self._modified_simulation is not None
            simulation = self.simulation
            modified_simulation = self._modified_simulation

        assert target_variable in self.tax_benefit_system.variables

        variables_belong_to_same_entity = (
            self.tax_benefit_system.variables[varying_variable].entity.key
            == self.tax_benefit_system.variables[target_variable].entity.key
            )
        varying_variable_belongs_to_person_entity = self.tax_benefit_system.variables[varying_variable].entity.is_person

        assert variables_belong_to_same_entity or varying_variable_belongs_to_person_entity

        if variables_belong_to_same_entity:
            modified_varying = modified_simulation.calculate_add(varying_variable, period = period)
            varying = simulation.calculate_add(varying_variable, period = period)
        else:
            target_variable_entity_key = self.tax_benefit_system.variables[target_variable].entity.key

            def cast_to_target_entity(simulation):
                population = simulation.populations[target_variable_entity_key]
                df = (pd.DataFrame(
                    {
                        'members_entity_id': population._members_entity_id,
                        varying_variable: simulation.calculate_add(varying_variable, period = period)
                        }
                    ).groupby('members_entity_id').sum())
                varying_variable_for_target_entity = df.loc[population.ids, varying_variable].values
                return varying_variable_for_target_entity

            modified_varying = cast_to_target_entity(modified_simulation)
            varying = cast_to_target_entity(simulation)

        modified_target = modified_simulation.calculate_add(target_variable, period = period)
        target = simulation.calculate_add(target_variable, period = period)

        numerator = modified_target - target
        denominator = modified_varying - varying
        marginal_rate = 1 - np.divide(
            numerator,
            denominator,
            out = np.full_like(numerator, value_for_zero_varying_variable, dtype = np.float),
            where = (denominator != 0)
            )

        return marginal_rate

    def compute_pivot_table(self, aggfunc = 'mean', columns = None, difference = False, filter_by = None, index = None,
            period = None, use_baseline = False, use_baseline_for_columns = None, values = None,
            missing_variable_default_value = np.nan, concat_axis = None, weighted = True, alternative_weights = None):
        """Computes a pivot table of agregated values casted along specified index and columns.

        Args:
          aggfunc(str, optional): Aggregation function, defaults to 'mean'
          columns(list, optional): Variable(s) in columns, defaults to None
          difference(bool, optional): Compute difference, defaults to False
          filter_by(str, optional): Boolean variable to filter by, defaults to None
          index(list, optional): Variable(s) in index (lines), defaults to None
          period(Period, optional): Period, defaults to None
          use_baseline(bool, optional): Compute for baseline, defaults to False
          use_baseline_for_columns(bool, optional): Use columns from baseline columns values, defaults to None
          values(list, optional): Aggregated variable(s) within cells, defaults to None
          missing_variable_default_value(float, optional): Default value for missing variables, defaults to np.nan
          concat_axis(int, optional): Axis to concatenate along (index = 0, columns = 1), defaults to None
          weighted(bool, optional): Whether to weight te aggregates (Default value = True)
          alternative_weights(str or int or float, optional): Weight variable name or numerical value. Use SurveyScenario's weight_variable_by_entity if None, and if the latetr is None uses 1 ((Default value = None)

        Returns:
          pd.DataFrame: Pivot table

        """

        assert aggfunc in ['count', 'mean', 'sum']
        assert columns or index or values
        assert not (difference and use_baseline), "Can't have difference and use_baseline both set to True"
        assert period is not None

        tax_benefit_system = self.baseline_tax_benefit_system if (
            use_baseline and self.baseline_tax_benefit_system
            ) else self.tax_benefit_system

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

        if filter_by is None and self.filtering_variable_by_entity is not None:
            filter_by = self.filtering_variable_by_entity.get(entity_key)

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

                elif type(alternative_weights) == int or type(alternative_weights) == float:
                    weight_variable = None
                    uniform_weight = float(alternative_weights)

            else:
                if self.weight_variable_by_entity:
                    weight_variable = self.weight_variable_by_entity[entity_key]
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
                filter_entity_key = assert_variables_in_same_entity(self, get_words(filter_by))
                expressions.extend([filter_by])
                assert filter_entity_key == entity_key
        else:
            filter_dummy = np.array(1.0)

        for expression in expressions:
            expression_variables = get_words(expression)
            expression_entity_key = assert_variables_in_same_entity(self, expression_variables)
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
            reform_data_frame = self.create_data_frame_by_entity(
                values, period = period, use_baseline = False, index = False
                )[entity_key].fillna(missing_variable_default_value)
            baseline_data_frame = self.create_data_frame_by_entity(
                values, period = period, use_baseline = True, index = False
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
                    self.create_data_frame_by_entity(
                        values, period = period, use_baseline = use_baseline, index = False)[entity_key]
                    )
                for value_variable in values:
                    if value_variable not in data_frame:
                        data_frame[value_variable] = missing_variable_default_value
            else:
                data_frame = None

        use_baseline_data = use_baseline or difference
        if use_baseline_for_columns is not None:
            use_baseline_data = use_baseline_for_columns

        baseline_vars_data_frame = self.create_data_frame_by_entity(
            variables = variables,
            period = period,
            # use baseline if explicited or when computing difference
            use_baseline = use_baseline_data,
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
        # We drop variables that are in values in baseline_vars_data_frame
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

    def create_data_frame_by_entity(self, variables = None, expressions = None, filter_by = None, index = False,
            period = None, use_baseline = False, merge = False):
        """Create dataframe(s) of computed variable for every entity (eventually merged in a unique dataframe)

        Args:
          variables(list, optional): Variable to compute, defaults to None
          expressions(str, optional): Expressions to compute, defaults to None
          filter_by(str, optional): Boolean variable or expression, defaults to None
          index(bool, optional): Index by entity id, defaults to False
          period(Period, optional): Period, defaults to None
          use_baseline(bool, optional): Use baseline tax and benefit system, defaults to False
          merge(bool, optional): Merge all the entities in one data frame, defaults to False

        Returns:
          dict or pandas.DataFrame: Dictionnary of dataframes by entities or dataframe with all the computed variables

        """
        simulation = self.baseline_simulation if (use_baseline and self.baseline_simulation) else self.simulation
        tax_benefit_system = self.baseline_tax_benefit_system if (
            use_baseline and self.baseline_tax_benefit_system
            ) else self.tax_benefit_system

        assert simulation is not None
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
                filter_entity_key = assert_variables_in_same_entity(self, get_words(filter_by))
                expressions.append(filter_by)

        expressions_by_entity_key = dict()
        for expression in expressions:
            expression_variables = get_words(expression)
            entity_key = assert_variables_in_same_entity(self, expression_variables)
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
                    (column_name, self.calculate_variable(
                        variable = column_name, period = period, use_baseline = use_baseline))
                    for column_name in column_names
                    )
                )
            if entity.is_person:
                person_entity = entity
            else:
                non_person_entities.append(entity)

        if index:
            person_data_frame = openfisca_data_frame_by_entity_key.get(person_entity.key)
            if person_data_frame is None:
                person_data_frame = pd.DataFrame()
            for entity in non_person_entities:
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

    def custom_input_data_frame(self, input_data_frame, **kwargs):
        """Customize input data frame.

        Args:
          input_data_frame: Original input data frame
          **kwargs: Keyword arguments
        """
        pass

    def dump_data_frame_by_entity(self, variables = None, survey_collection = None, survey_name = None):
        assert survey_collection is not None
        assert survey_name is not None
        assert variables is not None
        openfisca_data_frame_by_entity = self.create_data_frame_by_entity(variables = variables)
        for entity_key, data_frame in openfisca_data_frame_by_entity.items():
            survey = Survey(name = survey_name)
            survey.insert_table(name = entity_key, data_frame = data_frame)
            survey_collection.surveys.append(survey)
            survey_collection.dump(collection = "openfisca")

    def dump_simulations(self, directory = None):
        assert directory is not None
        use_sub_directories = True if self.baseline_simulation is not None else False

        if use_sub_directories:
            for use_baseline in [False, True]:
                sub_directory = 'baseline' if use_baseline else 'reform'
                self._dump_simulation(
                    directory = os.path.join(directory, sub_directory),
                    use_baseline = use_baseline,
                    )

        else:
            self._dump_simulation(directory = directory)

    def init_all_entities(self, tax_benefit_system, input_data_frame, builder, period = None):
        assert period is not None
        log.info('Initialasing simulation using input_data_frame for period {}'.format(period))

        if period.unit == YEAR:  # 1. year
            simulation = self.init_simulation_with_data_frame(
                tax_benefit_system,
                input_data_frame = input_data_frame,
                period = period,
                builder = builder,
                )
        elif period.unit == MONTH and period.size == 3:  # 2. quarter
            for offset in range(period.size):
                period_item = period.first_month.offset(offset, MONTH)
                simulation = self.init_simulation_with_data_frame(
                    tax_benefit_system,
                    input_data_frame = input_data_frame,
                    period = period_item,
                    builder = builder,
                    )
        elif period.unit == MONTH and period.size == 1:  # 3. months
            simulation = self.init_simulation_with_data_frame(
                tax_benefit_system,
                input_data_frame = input_data_frame,
                period = period,
                builder = builder,
                )
        else:
            raise ValueError("Invalid period {}".format(period))

        return simulation

    def filter_input_variables(self, input_data_frame = None):
        """Filter the input data frame from variables that won't be used or are set to be computed.

        Args:
          input_data_frame: Input dataframe (Default value = None)

        Returns:
          pd.DataFrame: filtered dataframe

        """
        assert input_data_frame is not None
        id_variable_by_entity_key = self.id_variable_by_entity_key
        role_variable_by_entity_key = self.role_variable_by_entity_key
        used_as_input_variables = self.used_as_input_variables

        tax_benefit_system = self.tax_benefit_system
        variables = tax_benefit_system.variables

        id_variables = [
            id_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]
        role_variables = [
            role_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]

        log.debug('Variable used_as_input_variables in filter: \n {}'.format(used_as_input_variables))

        unknown_columns = []
        for column_name in input_data_frame:
            if column_name in id_variables + role_variables:
                continue
            if column_name not in variables:
                unknown_columns.append(column_name)

        input_data_frame.drop(unknown_columns, axis = 1, inplace = True)

        if unknown_columns:
            log.debug('The following unknown columns {}, are dropped from input table'.format(
                sorted(unknown_columns)))

        used_columns = []
        dropped_columns = []
        for column_name in input_data_frame:
            if column_name in id_variables + role_variables:
                continue
            variable = variables[column_name]
            # Keeping the calculated variables that are initialized by the input data
            if variable.formulas:
                if column_name in used_as_input_variables:
                    used_columns.append(column_name)
                    continue

                dropped_columns.append(column_name)

        input_data_frame.drop(dropped_columns, axis = 1, inplace = True)

        if used_columns:
            log.debug(
                'These columns are not dropped because present in used_as_input_variables:\n {}'.format(
                    sorted(used_columns)))
        if dropped_columns:
            log.debug(
                'These columns in survey are set to be calculated, we drop them from the input table:\n {}'.format(
                    sorted(dropped_columns)))

        log.info('Keeping the following variables in the input_data_frame:\n {}'.format(
            sorted(list(input_data_frame.columns))))
        return input_data_frame

    def generate_performance_data(self, output_dir: str):
        if not self.trace:
            raise ValueError("Method generate_performance_data cannot be used if trace hasn't been activated.")
        reform_dir = os.path.join(output_dir, 'reform_perf_log')
        baseline_dir = os.path.join(output_dir, 'baseline_perf_log')
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        if not os.path.exists(reform_dir):
            os.mkdir(reform_dir)
        if not os.path.exists(baseline_dir):
            os.mkdir(baseline_dir)

        self.simulation.tracer.generate_performance_graph(reform_dir)
        self.simulation.tracer.generate_performance_tables(reform_dir)
        self.baseline_simulation.tracer.generate_performance_graph(baseline_dir)
        self.baseline_simulation.tracer.generate_performance_tables(baseline_dir)

    def inflate(self, inflator_by_variable = None, period = None, target_by_variable = None):
        assert inflator_by_variable or target_by_variable
        assert period is not None
        inflator_by_variable = dict() if inflator_by_variable is None else inflator_by_variable
        target_by_variable = dict() if target_by_variable is None else target_by_variable
        self.inflator_by_variable = inflator_by_variable
        self.target_by_variable = target_by_variable

        assert self.simulation is not None
        for use_baseline in [False, True]:
            if use_baseline:
                simulation = self.baseline_simulation
            else:
                assert self.simulation is not None
                simulation = self.simulation
                if (self.simulation == self.baseline_simulation):  # Avoid inflating two times
                    continue

            if simulation is None:
                continue

            tax_benefit_system = self.tax_benefit_system
            for variable_name in set(inflator_by_variable.keys()).union(set(target_by_variable.keys())):
                assert variable_name in tax_benefit_system.variables, \
                    "Variable {} is not a valid variable of the tax-benefit system".format(variable_name)
                if variable_name in target_by_variable:
                    inflator = inflator_by_variable[variable_name] = \
                        target_by_variable[variable_name] / self.compute_aggregate(
                            variable = variable_name, use_baseline = use_baseline, period = period)
                    log.info('Using {} as inflator for {} to reach the target {} '.format(
                        inflator, variable_name, target_by_variable[variable_name]))
                else:
                    assert variable_name in inflator_by_variable, 'variable_name is not in inflator_by_variable'
                    log.info('Using inflator {} for {}.  The target is thus {}'.format(
                        inflator_by_variable[variable_name],
                        variable_name, inflator_by_variable[variable_name] * self.compute_aggregate(
                            variable = variable_name, use_baseline = use_baseline, period = period)
                        ))
                    inflator = inflator_by_variable[variable_name]

                array = simulation.calculate_add(variable_name, period = period)
                assert array is not None
                simulation.delete_arrays(variable_name, period = period)  # delete existing arrays
                simulation.set_input(variable_name, period, inflator * array)  # insert inflated array

    def init_from_data(self, calibration_kwargs = None, inflation_kwargs = None,
            rebuild_input_data = False, rebuild_kwargs = None, data = None, memory_config = None, use_marginal_tax_rate = False):
        """Initialise a survey scenario from data.

        Args:
          rebuild_input_data(bool):  Whether or not to clean, format and save data. Take a look at :func:`build_input_data`
          data(dict): Contains the data, or metadata needed to know where to find it.
          use_marginal_tax_rate(bool): True to go into marginal effective tax rate computation mode.
          calibration_kwargs(dict):  Calibration options (Default value = None)
          inflation_kwargs(dict): Inflations options (Default value = None)
          rebuild_input_data(bool): Wether to rebuild the data (Default value = False)
          rebuild_kwargs:  Rebuild options (Default value = None)

        """
        # When not ``None``, it'll try to get the data for *year*.
        if data is not None:
            data_year = data.get("data_year", self.year)

        self._set_id_variable_by_entity_key()
        self._set_role_variable_by_entity_key()
        self._set_used_as_input_variables_by_entity()

        # When ``True`` it'll assume it is raw data and do all that described supra.
        # When ``False``, it'll assume data is ready for consumption.
        if rebuild_input_data:
            if rebuild_kwargs is not None:
                self.build_input_data(year = data_year, **rebuild_kwargs)
            else:
                self.build_input_data(year = data_year)

        debug = self.debug
        trace = self.trace

        if use_marginal_tax_rate:
            assert self.varying_variable in self.tax_benefit_system.variables

        # Inverting reform and baseline because we are more likely
        # to use baseline input in reform than the other way around
        if self.baseline_tax_benefit_system is not None:
            self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config,
                use_baseline = True)
            if use_marginal_tax_rate:
                self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config, use_baseline = True,
                    marginal_tax_rate_only = True)

        # Note that I can pass a :class:`pd.DataFrame` directly, if I don't want to rebuild the data.
        self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config)
        if use_marginal_tax_rate:
            self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config, marginal_tax_rate_only = True)

        if calibration_kwargs is not None:
            assert set(calibration_kwargs.keys()).issubset(set(
                ['target_margins_by_variable', 'parameters', 'total_population']))

        if inflation_kwargs is not None:
            assert set(inflation_kwargs.keys()).issubset(set(['inflator_by_variable', 'target_by_variable', 'period']))

        if calibration_kwargs:
            self.calibrate(**calibration_kwargs)

        if inflation_kwargs:
            self.inflate(**inflation_kwargs)

    def init_entity_structure(self, tax_benefit_system, entity, input_data_frame, builder):
        """Initialize sthe simulation with tax_benefit_system entities and input_data_frame.

        Args:
          tax_benefit_system(TaxBenfitSystem): The TaxBenefitSystem to get the structure from
          entity(Entity): The entity to initialize structure
          input_data_frame(pd.DataFrame): The input
          builder(Builder): The builder

        """
        id_variables = [
            self.id_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]
        role_variables = [
            self.role_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]

        if entity.is_person:
            for id_variable in id_variables + role_variables:
                assert id_variable in input_data_frame.columns, \
                    "Variable {} is not present in input dataframe".format(id_variable)

        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame)

        ids = range(len(input_data_frame))
        if entity.is_person:
            builder.declare_person_entity(entity.key, ids)
            for group_entity in tax_benefit_system.group_entities:
                _key = group_entity.key
                _id_variable = self.id_variable_by_entity_key[_key]
                _role_variable = self.role_variable_by_entity_key[_key]
                group_population = builder.declare_entity(_key, input_data_frame[_id_variable].drop_duplicates().sort_values().values)
                builder.join_with_persons(
                    group_population,
                    input_data_frame[_id_variable].astype('int').values,
                    input_data_frame[_role_variable].astype('int').values,
                    )

    def init_entity_data(self, entity, input_data_frame, period, simulation):
        used_as_input_variables = self.used_as_input_variables_by_entity[entity.key]
        diagnose_variable_mismatch(used_as_input_variables, input_data_frame)
        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame)

        for column_name, column_serie in input_data_frame.items():
            variable_instance = self.tax_benefit_system.variables.get(column_name)
            if variable_instance is None:
                continue

            if variable_instance.entity.key != entity.key:
                log.info("Ignoring variable {} which is not part of entity {} but {}".format(
                    column_name, entity.key, variable_instance.entity.key))
                continue
            init_variable_in_entity(simulation, entity.key, column_name, column_serie, period)

    def init_simulation_with_data_frame(self, tax_benefit_system, input_data_frame, period, builder):
        """Initialize the simulation period with current input_data_frame for an entity if specified."""
        used_as_input_variables = self.used_as_input_variables
        id_variable_by_entity_key = self.id_variable_by_entity_key
        role_variable_by_entity_key = self.role_variable_by_entity_key

        diagnose_variable_mismatch(used_as_input_variables, input_data_frame)

        id_variables = [
            id_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]
        role_variables = [
            role_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]

        for id_variable in id_variables + role_variables:
            assert id_variable in input_data_frame.columns, \
                "Variable {} is not present in input dataframe".format(id_variable)

        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame)

        index_by_entity_key = dict()

        for entity in tax_benefit_system.entities:
            self.init_entity_structure(tax_benefit_system, entity, input_data_frame, builder)

            if entity.is_person:
                continue

            else:
                index_by_entity_key[entity.key] = input_data_frame.loc[
                    input_data_frame[role_variable_by_entity_key[entity.key]] == 0,
                    id_variable_by_entity_key[entity.key]
                    ].sort_values().index

        for column_name, column_serie in input_data_frame.items():
            if role_variable_by_entity_key is not None:
                if column_name in role_variable_by_entity_key.values():
                    continue

            if id_variable_by_entity_key is not None:
                if column_name in id_variable_by_entity_key.values():
                    continue

            simulation = builder.build(tax_benefit_system)
            entity = tax_benefit_system.variables[column_name].entity
            if entity.is_person:
                init_variable_in_entity(simulation, entity.key, column_name, column_serie, period)
            else:
                init_variable_in_entity(simulation, entity.key, column_name, column_serie[index_by_entity_key[entity.key]], period)

        return simulation

    def new_simulation(self, debug = False, use_baseline = False, trace = False, data = None, memory_config = None, marginal_tax_rate_only = False):
        assert self.tax_benefit_system is not None
        tax_benefit_system = self.tax_benefit_system
        if self.baseline_tax_benefit_system is not None and use_baseline:
            tax_benefit_system = self.baseline_tax_benefit_system
        elif use_baseline:
            while True:
                baseline_tax_benefit_system = tax_benefit_system.baseline
                if isinstance(use_baseline, bool) and baseline_tax_benefit_system is None \
                        or baseline_tax_benefit_system == use_baseline:
                    break
                tax_benefit_system = baseline_tax_benefit_system

        period = periods.period(self.year)
        self.neutralize_variables(tax_benefit_system)
        #
        simulation = self.init_simulation(tax_benefit_system, period, data)
        simulation.debug = debug
        simulation.trace = trace
        simulation.opt_out_cache = True if self.cache_blacklist is not None else False
        simulation.memory_config = memory_config

        #
        if marginal_tax_rate_only:
            self._apply_modification(simulation, period)
            if not use_baseline:
                self._modified_simulation = simulation
            else:
                self._modified_baseline_simulation = simulation
        else:
            if not use_baseline:
                self.simulation = simulation
            else:
                self.baseline_simulation = simulation
            #
        if 'custom_initialize' in dir(self):
            self.custom_initialize(simulation)
        #
        return simulation

    def init_simulation(self, tax_benefit_system, period, data):
        builder = SimulationBuilder()
        builder.create_entities(tax_benefit_system)

        data_year = data.get("data_year", self.year)
        survey = data.get('survey')

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
            simulation = self.init_all_entities(tax_benefit_system, source, builder, period)

        if source_type == 'input_data_table':
            # Case 1: fill simulation with a unique input_data_frame given by the attribute
            if input_data_survey_prefix is not None:
                openfisca_survey_collection = SurveyCollection.load(collection = self.collection)
                openfisca_survey = openfisca_survey_collection.get_survey("{}_{}".format(
                    input_data_survey_prefix, data_year))
                input_data_frame = openfisca_survey.get_values(table = "input").reset_index(drop = True)
            else:
                NotImplementedError

            self.custom_input_data_frame(input_data_frame, period = period)
            simulation = self.init_all_entities(tax_benefit_system, input_data_frame, builder, period)  # monolithic dataframes

        elif source_type == 'input_data_table_by_period':
            # Case 2: fill simulation with input_data_frame by period containing all entity variables
            for period, table in self.input_data_table_by_period.items():
                period = periods.period(period)
                log.debug('From survey {} loading table {}'.format(survey, table))
                input_data_frame = self.load_table(survey = survey, table = table)
                self.custom_input_data_frame(input_data_frame, period = period)
                simulation = self.init_all_entities(tax_benefit_system, input_data_frame, builder, period)  # monolithic dataframes

        elif source_type == 'input_data_frame_by_entity_by_period':
            for period, input_data_frame_by_entity in source.items():
                period = periods.period(period)
                for entity in tax_benefit_system.entities:
                    input_data_frame = input_data_frame_by_entity.get(entity.key)
                    if input_data_frame is None:
                        continue
                    self.custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                    self.init_entity_structure(tax_benefit_system, entity, input_data_frame, builder)

            simulation = builder.build(tax_benefit_system)
            for period, input_data_frame_by_entity in source.items():
                for entity in tax_benefit_system.entities:
                    input_data_frame = input_data_frame_by_entity.get(entity.key)
                    if input_data_frame is None:
                        log.debug("No input_data_frame found for entity {} at period {}".format(entity, period))
                        continue
                    self.custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                    self.init_entity_data(entity, input_data_frame, period, simulation)

        elif source_type == 'input_data_table_by_entity_by_period':
            # Case 3: fill simulation with input_data_table by entity_by_period containing a dictionnary
            # of all periods containing a dictionnary of entity variables
            input_data_table_by_entity_by_period = source
            simulation = None
            for period, input_data_table_by_entity in input_data_table_by_entity_by_period.items():
                period = periods.period(period)

                if simulation is None:
                    for entity in tax_benefit_system.entities:
                        table = input_data_table_by_entity.get(entity.key)
                        if table is None:
                            continue
                        if survey is not None:
                            input_data_frame = self.load_table(survey = survey, table = table)
                        else:
                            input_data_frame = self.load_table(survey = 'input', table = table)
                        self.custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                        self.init_entity_structure(tax_benefit_system, entity, input_data_frame, builder)

                    simulation = builder.build(tax_benefit_system)

                for entity in tax_benefit_system.entities:
                    table = input_data_table_by_entity.get(entity.key)
                    if table is None:
                        continue
                    if survey is not None:
                        input_data_frame = self.load_table(survey = survey, table = table)
                    else:
                        input_data_frame = self.load_table(survey = 'input', table = table)
                    self.custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                    self.init_entity_data(entity, input_data_frame, period, simulation)
        else:
            pass

        if self.year is not None:
            simulation.period = periods.period(self.year)

        return simulation

    def load_table(self, variables = None, collection = None, survey = None,
            table = None):
        collection = collection or self.collection
        survey_collection = SurveyCollection.load(collection = self.collection)
        if survey is not None:
            survey = survey
        else:
            survey = "{}_{}".format(self.input_data_survey_prefix, self.year)
        survey_ = survey_collection.get_survey(survey)
        log.debug("Loading table {} in survey {} from collection {}".format(table, survey, collection))
        return survey_.get_values(table = table, variables = variables)

    def memory_usage(self, use_baseline = False):
        if use_baseline:
            simulation = self.baseline_simulation
        else:
            simulation = self.simulation

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
            print(line.rjust(100))

    def neutralize_variables(self, tax_benefit_system):
        """Neutralizes input variables not in input dataframe and keep some crucial variables

        Args:
          tax_benefit_system: The TaxBenefitSystem variables belongs to

        """
        for variable_name, variable in tax_benefit_system.variables.items():
            if variable.formulas:
                continue
            if self.used_as_input_variables and (variable_name in self.used_as_input_variables):
                continue
            if self.non_neutralizable_variables and (variable_name in self.non_neutralizable_variables):
                continue
            if self.weight_variable_by_entity and (variable_name in self.weight_variable_by_entity.values()):
                continue

            tax_benefit_system.neutralize_variable(variable_name)

    def restore_simulations(self, directory, **kwargs):
        """Restores SurveyScenario's simulations

        Args:
          directory: Directory to restore simulations from
          **kwargs: Restoration options

        """
        assert os.path.exists(directory), "Cannot restore simulations from non existent directory"

        use_sub_directories = os.path.exists(os.path.join(directory, 'baseline'))
        if use_sub_directories:
            for use_baseline in [False, True]:
                sub_directory = 'baseline' if use_baseline else 'reform'
                print(os.path.join(directory, sub_directory), use_baseline)
                self._restore_simulation(
                    directory = os.path.join(directory, sub_directory),
                    use_baseline = use_baseline,
                    **kwargs
                    )
        else:
            self._restore_simulation(
                directory = directory,
                **kwargs
                )

    def set_input_data_frame(self, input_data_frame):
        """Sets the input dataframe

        Args:
          input_data_frame (pd.DataFrame): Input data frame

        """
        self.input_data_frame = input_data_frame

    def set_tax_benefit_systems(self, tax_benefit_system = None, baseline_tax_benefit_system = None):
        """Sets the tax and benefit system and eventually the baseline tax and benefit system

        Args:
          tax_benefit_system: The main tax benefit system (Default value = None)
          baseline_tax_benefit_system: The baseline tax benefit system (Default value = None)
        """
        assert tax_benefit_system is not None
        self.tax_benefit_system = tax_benefit_system
        if self.cache_blacklist is not None:
            self.tax_benefit_system.cache_blacklist = self.cache_blacklist
        if baseline_tax_benefit_system is not None:
            self.baseline_tax_benefit_system = baseline_tax_benefit_system
            if self.cache_blacklist is not None:
                self.baseline_tax_benefit_system.cache_blacklist = self.cache_blacklist

    def summarize_variable(self, variable = None, use_baseline = False, weighted = False, force_compute = False):
        """Prints a summary of a variable including its memory usage.

        Args:
          variable(string): The variable being summarized
          use_baseline(bool): The tax-benefit-system considered
          weighted(bool): Whether the produced statistics should be weigthted or not
          force_compute(bool): Whether the computation of the variable should be forced

        Example:
            >>> from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
            >>> survey_scenario = create_randomly_initialized_survey_scenario()
            >>> survey_scenario.summarize_variable(variable = "housing_occupancy_status", force_compute = True)
            <BLANKLINE>
            housing_occupancy_status: 1 periods * 5 cells * item size 2 (int16, default = HousingOccupancyStatus.tenant) = 10B
            Details:
            2017-01: owner = 0.00e+00 (0.0%), tenant = 5.00e+00 (100.0%), free_lodger = 0.00e+00 (0.0%), homeless = 0.00e+00 (0.0%).
            >>> survey_scenario.summarize_variable(variable = "rent", force_compute = True)
            <BLANKLINE>
            rent: 2 periods * 5 cells * item size 4 (float32, default = 0) = 40B
            Details:
            2017-01: mean = 562.385107421875, min = 156.01864624023438, max = 950.7142944335938, mass = 2.81e+03, default = 0.0%, median = 598.6585083007812
            2018-01: mean = 562.385107421875, min = 156.01864624023438, max = 950.7142944335938, mass = 2.81e+03, default = 0.0%, median = 598.6585083007812
            >>> survey_scenario.tax_benefit_system.neutralize_variable('age')
            >>> survey_scenario.summarize_variable(variable = "age")
            <BLANKLINE>
            age: neutralized variable (int64, default = 0)
        """

        if use_baseline:
            simulation = self.baseline_simulation
        else:
            simulation = self.simulation

        tax_benefit_system = simulation.tax_benefit_system
        variable_instance = tax_benefit_system.variables.get(variable)
        assert variable_instance is not None, "{} is not a valid variable".format(variable)

        default_value = variable_instance.default_value
        value_type = variable_instance.value_type

        if variable_instance.is_neutralized:
            print("")
            print("{}: neutralized variable ({}, default = {})".format(variable, str(np.dtype(value_type)), default_value))
            return

        if weighted:
            weight_variable = self.weight_variable_by_entity[variable_instance.entity.key]
            weights = simulation.calculate(weight_variable, simulation.period)

        infos = simulation.get_memory_usage(variables = [variable])['by_variable'].get(variable)
        if not infos:
            if force_compute:
                self.calculate_variable(variable = variable, period = simulation.period, use_baseline = use_baseline)
                self.summarize_variable(variable = variable, use_baseline = use_baseline, weighted = weighted)
                return
            else:
                print("{} is not computed yet. Use keyword argument force_compute = True".format(variable))
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
        print("")
        print(header_line)
        print("Details:")
        holder = simulation.get_holder(variable)
        if holder is not None:
            if holder.variable.definition_period == ETERNITY:
                array = holder.get_array(ETERNITY)
                print("permanent: mean = {}, min = {}, max = {}, median = {}, default = {:.1%}".format(
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
                        print("{}: always = {}".format(period, array))
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
                        print("{}:{}.".format(period, ",".join(expr)))
                        continue

                    print("{}: mean = {}, min = {}, max = {}, mass = {:.2e}, default = {:.1%}, median = {}".format(
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

    def _apply_modification(self, simulation, period):
        period = periods.period(period)
        varying_variable = self.varying_variable
        definition_period = simulation.tax_benefit_system.variables[varying_variable].definition_period

        def set_variable(varying_variable, varying_variable_value, period_):
            delta = self.variation_factor * varying_variable_value
            new_variable_value = varying_variable_value + delta
            simulation.delete_arrays(varying_variable, period_)
            simulation.set_input(varying_variable, period_, new_variable_value)

        if period.unit == definition_period:
            varying_variable_value = simulation.calculate(varying_variable, period = period)
            set_variable(varying_variable, varying_variable_value, period)

        elif (definition_period == MONTH) and (period.unit == YEAR and period.size_in_months == 12):
            varying_variable_value = simulation.calculate_add(varying_variable, period = period)
            for period_ in [periods.Period(('month', period.start.offset(month, 'month'), 1)) for month in range(12)]:
                set_variable(varying_variable, varying_variable_value / 12, period_)
        else:
            ValueError()

    def _dump_simulation(self, directory = None, use_baseline = False):
        assert directory is not None
        if use_baseline:
            assert self.baseline_simulation is not None
            dump_simulation(self.baseline_simulation, directory)
        else:
            assert self.simulation is not None
            dump_simulation(self.simulation, directory)

    def _restore_simulation(self, directory = None, use_baseline = False, **kwargs):
        assert directory is not None
        if use_baseline:
            assert self.baseline_tax_benefit_system is not None
            self.baseline_simulation = restore_simulation(
                directory,
                self.baseline_tax_benefit_system,
                **kwargs
                )
        else:
            assert self.tax_benefit_system is not None
            self.simulation = restore_simulation(
                directory,
                self.tax_benefit_system,
                **kwargs
                )

    def _set_id_variable_by_entity_key(self) -> Dict[str, str]:
        """Identifies and sets the correct ids for the different entities"""
        if self.id_variable_by_entity_key is None:
            log.debug("Use default id_variable names")
            self.id_variable_by_entity_key = dict(
                (entity.key, entity.key + '_id') for entity in self.tax_benefit_system.entities)

        return self.id_variable_by_entity_key

    def _set_role_variable_by_entity_key(self) -> Dict[str, str]:
        """Identifies and sets the correct roles for the different entities"""
        if self.role_variable_by_entity_key is None:
            self.role_variable_by_entity_key = dict(
                (entity.key, entity.key + '_role_index') for entity in self.tax_benefit_system.entities)

        return self.role_variable_by_entity_key

    def _set_used_as_input_variables_by_entity(self) -> Dict[str, List[str]]:
        """Identifies and sets the correct input variables for the different entities"""
        if self.used_as_input_variables_by_entity is not None:
            return

        tax_benefit_system = self.tax_benefit_system

        assert set(self.used_as_input_variables) <= set(tax_benefit_system.variables.keys()), \
            "Some variables used as input variables are not part of the tax benefit system:\n {}".format(
                set(self.used_as_input_variables).difference(set(tax_benefit_system.variables.keys()))
                )

        self.used_as_input_variables_by_entity = dict()

        for entity in tax_benefit_system.entities:
            self.used_as_input_variables_by_entity[entity.key] = [
                variable
                for variable in self.used_as_input_variables
                if tax_benefit_system.get_variable(variable).entity.key == entity.key
                ]

        return self.used_as_input_variables_by_entity


# Helpers

def get_words(text):
    return re.compile('[A-Za-z_]+').findall(text)


def assert_variables_in_same_entity(survey_scenario, variables):
    """Asserts taht variables are in the same entity

    Args:
      survey_scenario: Host SurveyScenario
      variables: Variables to check presence

    Returns:
      str: Unique entity key if variables all belongs to it

    """
    entity = None
    for variable_name in variables:
        variable = survey_scenario.tax_benefit_system.variables.get(variable_name)
        assert variable
        if entity is None:
            entity = variable.entity
        assert variable.entity == entity, "{} are not from the same entity: {} doesn't belong to {}".format(
            variables, variable_name, entity.key)
    return entity.key


def init_variable_in_entity(simulation, entity, variable_name, series, period):
    variable = simulation.tax_benefit_system.variables[variable_name]

    # np.issubdtype cannot handles categorical variables
    if (not pd.api.types.is_categorical_dtype(series)) and np.issubdtype(series.values.dtype, np.floating):
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
            pd.api.types.is_categorical_dtype(series)
            or not (
                np.issubdtype(series.values.dtype, np.integer)
                or np.issubdtype(series.values.dtype, np.float)
                )
            )
        )

    if enum_variable_imputed_as_enum:
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
    # TODO is the next line needed ?
    # Might be due to values returning also ndarray like objects
    # for instance for categories or
    np_array = np.array(array, dtype = variable.dtype)
    if variable.definition_period == YEAR and period.unit == MONTH:
        # Some variables defined for a year are present in month/quarter dataframes
        # Cleaning the dataframe would probably be better in the long run
        log.warn('Trying to set a monthly value for variable {}, which is defined on a year. The  montly values you provided will be summed.'
            .format(variable_name).encode('utf-8'))

        if simulation.get_array(variable_name, period.this_year) is not None:
            array_sum = simulation.get_array(variable_name, period.this_year) + np_array
            simulation.set_input(variable_name, period.this_year, array_sum)
        else:
            simulation.set_input(variable_name, period.this_year, np_array)

    else:
        simulation.set_input(variable_name, period, np_array)


def diagnose_variable_mismatch(used_as_input_variables, input_data_frame):
    """Diagnose variables mismatch.

    Args:
      used_as_input_variables(lsit): List of variable to test presence
      input_data_frame: DataFrame in which to test variables presence

    """
    variables_mismatch = set(used_as_input_variables).difference(set(input_data_frame.columns)) if used_as_input_variables else None
    if variables_mismatch:
        log.info(
            'The following variables are used as input variables are not present in the input data frame: \n {}'.format(
                sorted(variables_mismatch)))
    if variables_mismatch:
        log.debug('The following variables are used as input variables: \n {}'.format(
            sorted(used_as_input_variables)))
        log.debug('The input_data_frame contains the following variables: \n {}'.format(
            sorted(list(input_data_frame.columns))))
