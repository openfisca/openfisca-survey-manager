# -*- coding: utf-8 -*-

from __future__ import division

import logging
import os
import numpy as np
import pandas as pd
import re


import humanize


from openfisca_core import periods, simulations
from openfisca_core.periods import MONTH, YEAR, ETERNITY
from openfisca_core.tools.simulation_dumper import dump_simulation, restore_simulation

from openfisca_survey_manager.calibration import Calibration

from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey

log = logging.getLogger(__name__)


class AbstractSurveyScenario(object):
    debug = False
    filtering_variable_by_entity = None
    id_variable_by_entity_key = None
    inflator_by_variable = None  # factor used to inflate variable total
    input_data_frame = None
    input_data_table_by_period = None
    input_data_table_by_entity_by_period = None
    non_neutralizable_variables = None
    cache_blacklist = None
    baseline_simulation = None
    baseline_tax_benefit_system = None
    role_variable_by_entity_key = None
    simulation = None
    target_by_variable = None  # variable total target to inflate to
    tax_benefit_system = None
    trace = False
    used_as_input_variables = None
    used_as_input_variables_by_entity = None
    weight_column_name_by_entity = None
    year = None

    def calibrate(self, target_margins_by_variable = None, parameters = None, total_population = None):
        survey_scenario = self
        survey_scenario.initialize_weights()
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
            difference = False, missing_variable_default_value = np.nan):
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
                    ) -
                self.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    use_baseline = True,
                    missing_variable_default_value = missing_variable_default_value,
                    )
                )

        tax_benefit_system = self.tax_benefit_system
        if filter_by is None and self.filtering_variable_by_entity is not None:
            entity_key = tax_benefit_system.variables[variable].entity.key
            filter_by = self.filtering_variable_by_entity.get(entity_key)

        assert variable is not None
        if use_baseline:
            simulation = self.baseline_simulation
        else:
            simulation = self.simulation

        assert simulation is not None
        if period is None:
            period = simulation.period

        if filter_by:
            assert filter_by in self.tax_benefit_system.variables, \
                "{} is not a variables of the tax benefit system".format(filter_by)

        if self.weight_column_name_by_entity:
            weight_column_name_by_entity = self.weight_column_name_by_entity
            entity_key = tax_benefit_system.variables[variable].entity.key
            entity_weight = weight_column_name_by_entity[entity_key]
        else:
            entity_weight = None

        if variable in simulation.tax_benefit_system.variables:
            value = self.calculate_variable(variable = variable, period = period, use_baseline = use_baseline)
        else:
            log.info("Variable {} not found. Assiging {}".format(variable, missing_variable_default_value))
            return missing_variable_default_value

        weight = (
            self.calculate_variable(
                variable = entity_weight, period = period, use_baseline = use_baseline
                ).astype(float)
            if entity_weight else 1.0
            )
        filter_dummy = self.calculate_variable(variable = filter_by, period = period) if filter_by else 1.0

        if aggfunc == 'sum':
            return (value * weight * filter_dummy).sum()
        elif aggfunc == 'mean':
            return (value * weight * filter_dummy).sum() / (weight * filter_dummy).sum()
        elif aggfunc == 'count':
            return (weight * filter_dummy).sum()
        elif aggfunc == 'count_non_zero':
            return (weight * (value != 0) * filter_dummy).sum()

    def compute_pivot_table(self, aggfunc = 'mean', columns = None, difference = False, filter_by = None, index = None,
            period = None, use_baseline = False, values = None, missing_variable_default_value = np.nan):
        assert aggfunc in ['count', 'mean', 'sum']
        assert columns or index or values
        assert not (difference and use_baseline), "Can't have difference and use_baseline both set to True"
        assert period is not None

        tax_benefit_system = self.tax_benefit_system

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
            if axe is not None and entity_key is None:
                entity_key = tax_benefit_system.variables[axe[0]].entity.key

        if filter_by is None and self.filtering_variable_by_entity is not None:
            filter_by = self.filtering_variable_by_entity.get(entity_key)

        variables = set(index + values + columns)
        # Select the entity weight corresponding to the variables that will provide values
        if self.weight_column_name_by_entity is not None:
            weight = self.weight_column_name_by_entity[entity_key]
            variables.add(weight)
        else:
            log.debug('There is no weight variable for entity {}'.format(entity_key))
            weight = None

        if filter_by is not None:
            variables.add(filter_by)
        else:
            filter_dummy = 1.0

        for variable in variables:
            assert tax_benefit_system.variables[variable].entity.key == entity_key, \
                'The variable {} is not present or does not belong to entity {}'.format(
                    variable,
                    entity_key,
                    )

        if difference:
            data_frame = (
                self.create_data_frame_by_entity(
                    values, period = period, use_baseline = False, index = False)[entity_key] -
                self.create_data_frame_by_entity(
                    values, period = period, use_baseline = True, index = False)[entity_key]
                )
        else:
            data_frame = (
                self.create_data_frame_by_entity(
                    values, period = period, use_baseline = use_baseline, index = False)[entity_key]
                )
        additionnal_variables = []
        if filter_by is not None:
            additionnal_variables.append(filter_by)
        if weight is not None:
            additionnal_variables.append(weight)
        reference_variables = set(index + columns + additionnal_variables)
        data_frame = pd.concat(
            [
                self.create_data_frame_by_entity(
                    variables = reference_variables,
                    period = period,
                    # use baseline if explicited or when computing difference
                    use_baseline = use_baseline or difference,
                    index = False
                    )[entity_key],
                data_frame,
                ],
            axis = 1,
            )
        if filter_by in data_frame:
            filter_dummy = data_frame[filter_by]

        if weight is None:
            weight = 'weight'
            data_frame[weight] = 1.0

        data_frame[weight] = data_frame[weight] * filter_dummy

        if values:
            data_frame_by_value = dict()
            for value in values:
                data_frame[value] = data_frame[value] * data_frame[weight]
                data_frame[value].fillna(missing_variable_default_value)
                pivot_sum = data_frame.pivot_table(index = index, columns = columns, values = values, aggfunc = 'sum')
                pivot_mass = data_frame.pivot_table(index = index, columns = columns, values = weight, aggfunc = 'sum')
                if aggfunc == 'mean':
                    try:  # Deal with a pivot_table pandas bug https://github.com/pandas-dev/pandas/issues/17038
                        result = (pivot_sum / pivot_mass.loc[weight])
                    except KeyError:
                        result = (pivot_sum / pivot_mass)
                elif aggfunc == 'sum':
                    result = pivot_sum
                elif aggfunc == 'count':
                    result = pivot_mass

                data_frame_by_value[value] = result

            if len(list(data_frame_by_value.keys())) > 1:
                return data_frame_by_value
            else:
                return next(iter(data_frame_by_value.values()))

        else:
            assert aggfunc == 'count', "Can only use count for aggfunc if no values"
            return data_frame.pivot_table(index = index, columns = columns, values = weight, aggfunc = 'sum')

    def calculate_variable(self, variable = None, period = None, use_baseline = False):
        """
        Compute and return the variable values for period and baseline or reform tax_benefit_system
        """
        if use_baseline:
            assert self.baseline_simulation is not None, "self.baseline_simulation is None"
            simulation = self.baseline_simulation
        else:
            assert self.simulation is not None
            simulation = self.simulation

        tax_benefit_system = simulation.tax_benefit_system

        assert period is not None
        if not isinstance(period, periods.Period):
            period = periods.period(period)
        assert simulation is not None
        assert tax_benefit_system is not None

        assert variable in tax_benefit_system.variables, "{} is not a valid variable".format(variable)
        period_size_independent = tax_benefit_system.get_variable(variable).is_period_size_independent
        definition_period = tax_benefit_system.get_variable(variable).definition_period

        if period_size_independent is False and definition_period != u'eternity':
            values = simulation.calculate_add(variable, period = period)
        elif period_size_independent is True and definition_period == u'month' and period.size_in_months > 1:
            values = simulation.calculate(variable, period = period.first_month)
        elif period_size_independent is True and definition_period == u'month' and period.size_in_months == 1:
            values = simulation.calculate(variable, period = period)
        elif period_size_independent is True and definition_period == u'year' and period.size_in_months > 12:
            values = simulation.calculate(variable, period = period.start.offset('first-of', 'year').period('year'))
        elif period_size_independent is True and definition_period == u'year' and period.size_in_months == 12:
            values = simulation.calculate(variable, period = period)
        elif definition_period == u'eternity':
            values = simulation.calculate(variable, period = period)
        else:
            values = None
        assert values is not None, 'Unspecified calculation period for variable {}'.format(variable)

        return values

    def create_data_frame_by_entity(self, variables = None, expressions = None, filter_by = None, index = False,
            period = None, use_baseline = False, merge = False, ignore_missing_variables = False):

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
            log.info("These variables aren't par of the tax-benefit system: {}".format(missing_variables))
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
                if column.entity == entity
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
                    ] = simulation.entities[entity.key].members_entity_id
                person_data_frame[
                    "{}_{}".format(entity.key, 'role')
                    ] = simulation.entities[entity.key].members_legacy_role
                person_data_frame[
                    "{}_{}".format(entity.key, 'position')
                    ] = simulation.entities[entity.key].members_position

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
        use_sub_directories = self.baseline_simulation is not None
        for use_baseline in [False, True]:
            if use_baseline and not use_sub_directories:
                continue
            if use_sub_directories:
                sub_directory = 'baseline' if use_baseline else 'reform'
                directory = os.path.join(directory, sub_directory)

            self._dump_simulation(directory = directory, use_baseline = use_baseline)


    def init_all_entities(self, input_data_frame, simulation, period = None, entity = None):
        assert period is not None
        if entity:
            log.info('Initialasing simulation using input_data_frame for entity {} for period {}'.format(
                entity, period))
        else:
            log.info('Initialasing simulation using input_data_frame for period {}'.format(period))

        if period.unit == YEAR:  # 1. year
            self.init_simulation_with_data_frame(
                input_data_frame = input_data_frame,
                period = period,
                simulation = simulation,
                entity = entity,
                )
        elif period.unit == MONTH and period.size == 3:  # 2. quarter
            for offset in range(period.size):
                period_item = period.first_month.offset(offset, MONTH)
                self.init_simulation_with_data_frame(
                    input_data_frame = input_data_frame,
                    period = period_item,
                    simulation = simulation,
                    entity = entity,
                    )
        elif period.unit == MONTH and period.size == 1:  # 3. months
            self.init_simulation_with_data_frame(
                input_data_frame = input_data_frame,
                period = period,
                simulation = simulation,
                entity = entity,
                )
        else:
            log.info("Invalid period {}".format(period))
            raise()

    def filter_input_variables(self, input_data_frame = None, simulation = None):
        """
        Filter the input data frame from variables that won't be used or are set to be computed
        """
        assert input_data_frame is not None
        assert simulation is not None
        id_variable_by_entity_key = self.id_variable_by_entity_key
        role_variable_by_entity_key = self.role_variable_by_entity_key
        used_as_input_variables = self.used_as_input_variables

        tax_benefit_system = simulation.tax_benefit_system
        variables = tax_benefit_system.variables

        id_variables = [
            id_variable_by_entity_key[_entity.key] for _entity in simulation.entities.values()
            if not _entity.is_person]
        role_variables = [
            role_variable_by_entity_key[_entity.key] for _entity in simulation.entities.values()
            if not _entity.is_person]

        log.debug('Variable used_as_input_variables in filter: \n {}'.format(used_as_input_variables))

        unknown_columns = []
        for column_name in input_data_frame:
            if column_name in id_variables + role_variables:
                continue
            if column_name not in variables:
                unknown_columns.append(column_name)
                input_data_frame.drop(column_name, axis = 1, inplace = True)

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
                input_data_frame.drop(column_name, axis = 1, inplace = True)
                #
            #
        #
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

    def inflate(self, inflator_by_variable = None, period = None, target_by_variable = None):
        assert inflator_by_variable or target_by_variable
        assert period is not None
        inflator_by_variable = dict() if inflator_by_variable is None else inflator_by_variable
        target_by_variable = dict() if target_by_variable is None else target_by_variable
        self.inflator_by_variable = inflator_by_variable
        self.target_by_variable = target_by_variable

        assert self.simulation is not None
        for use_baseline in [False, True]:
            if use_baseline is True:
                simulation = self.baseline_simulation
            else:
                assert self.simulation is not None
                simulation = self.simulation
            if simulation is None:
                continue
            tax_benefit_system = self.tax_benefit_system
            for variable_name in set(inflator_by_variable.keys()).union(set(target_by_variable.keys())):
                assert variable_name in tax_benefit_system.variables, \
                    "Variable {} is not a valid variable of the tax-benefit system".format(variable_name)
                holder = simulation.get_holder(variable_name)
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

                array = holder.get_array(period)
                if array is None:
                    array = simulation.calculate_add(variable_name, period = period)
                assert array is not None
                holder.delete_arrays(period = period)  # delete existing arrays
                simulation.set_input(variable_name, period, inflator * array)  # insert inflated array

    def init_from_data(self, calibration_kwargs = None, inflation_kwargs = None,
            rebuild_input_data = False, rebuild_kwargs = None, data = None, memory_config = None):

        if data is not None:
            data_year = data.get("data_year", self.year)

        if calibration_kwargs is not None:
            assert set(calibration_kwargs.keys()).issubset(set(
                ['target_margins_by_variable', 'parameters', 'total_population']))

        if inflation_kwargs is not None:
            assert set(inflation_kwargs.keys()).issubset(set(['inflator_by_variable', 'target_by_variable']))

        self._set_ids_and_roles_variables()
        self._set_used_as_input_variables_by_entity()
        if rebuild_input_data:
            if rebuild_kwargs is not None:
                self.build_input_data(year = data_year, **rebuild_kwargs)
            else:
                self.build_input_data(year = data_year)

        debug = self.debug
        trace = self.trace
        self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config)
        if self.baseline_tax_benefit_system is not None:
            self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config,
                use_baseline = True)
        #
        if calibration_kwargs:
            self.calibrate(**calibration_kwargs)

        if inflation_kwargs:
            self.inflate(**inflation_kwargs)

    def init_entity(self, entity = None, input_data_frame = None, period = None, simulation = None):
        """
        Initialize the simulation period with current input_data_frame
        """
        assert entity is not None
        assert input_data_frame is not None
        assert period is not None
        assert simulation is not None
        used_as_input_variables = self.used_as_input_variables_by_entity[entity]

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

        entity = simulation.entities[entity]
        id_variables = [
            self.id_variable_by_entity_key[_entity.key] for _entity in simulation.entities.values()
            if not _entity.is_person]
        role_variables = [
            self.role_variable_by_entity_key[_entity.key] for _entity in simulation.entities.values()
            if not _entity.is_person]

        if entity.is_person:
            for id_variable in id_variables + role_variables:
                assert id_variable in input_data_frame.columns, \
                    "Variable {} is not present in input dataframe".format(id_variable)

        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame, simulation = simulation)

        if entity.is_person:
            entity.count = entity.step_size = len(input_data_frame)
            for collective_entity in simulation.entities.values():
                if collective_entity.is_person:
                    continue
                _key = collective_entity.key
                _id_variable = self.id_variable_by_entity_key[_key]
                _role_variable = self.role_variable_by_entity_key[_key]
                collective_entity.roles_count = int(input_data_frame[_role_variable].max() + 1)
                assert isinstance(collective_entity.roles_count, int), \
                    '{} is not a valid roles_count (int) for {}'.format(collective_entity.roles_count, _key)

                collective_entity.count = len(input_data_frame[_id_variable].unique())
                collective_entity.members_entity_id = input_data_frame[_id_variable].astype('int').values
                # TODO legacy use
                collective_entity.members_legacy_role = input_data_frame[_role_variable].astype('int').values

        else:
            entity.count = entity.step_size = len(input_data_frame)

        for column_name, column_serie in input_data_frame.items():
            if column_name in (id_variables + role_variables):
                continue

            variable_instance = self.tax_benefit_system.variables.get(column_name)
            if variable_instance.entity.key != entity.key:
                log.info("Ignoring variable {} which is not part of entity {} but {}".format(
                    column_name, entity.key, variable_instance.entity.key))
                continue

            init_variable_in_entity(
                entity = entity,
                variable_name = column_name,
                series = column_serie,
                period = period,
                )

    def init_simulation_with_data_frame(self, input_data_frame = None, period = None, simulation = None, entity = None):
        """
        Initialize the simulation period with current input_data_frame for an entity if specified
        """
        assert input_data_frame is not None
        assert period is not None
        assert simulation is not None
        used_as_input_variables = self.used_as_input_variables
        id_variable_by_entity_key = self.id_variable_by_entity_key
        role_variable_by_entity_key = self.role_variable_by_entity_key

        variables_mismatch = set(used_as_input_variables).difference(set(input_data_frame.columns))
        if variables_mismatch:
            log.info(
                'The following variables used as input variables are not present in the input data frame: \n {}'.format(
                    sorted(variables_mismatch)))
        if variables_mismatch:
            log.debug('The following variables are used as input variables: \n {}'.format(
                sorted(used_as_input_variables)))
            log.debug('The input_data_frame contains the following variables: \n {}'.format(
                sorted(list(input_data_frame.columns))))

        id_variables = [
            id_variable_by_entity_key[_entity.key] for _entity in simulation.entities.values()
            if not _entity.is_person]
        role_variables = [
            role_variable_by_entity_key[_entity.key] for _entity in simulation.entities.values()
            if not _entity.is_person]

        for id_variable in id_variables + role_variables:
            entity_key = entity.key if entity is not None else None
            if (entity_key is not None) and (not simulation.entities[entity].is_person):
                assert id_variable in [id_variable_by_entity_key[entity], role_variable_by_entity_key[entity]], \
                    "variable {} for entity {} is not valid (not {} nor {})".format(
                        id_variable,
                        entity_key,
                        id_variable_by_entity_key[entity_key],
                        role_variable_by_entity_key[entity_key],
                        )
                continue
            assert id_variable in input_data_frame.columns, \
                "Variable {} is not present in input dataframe".format(id_variable)

        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame, simulation = simulation)

        index_by_entity_key = dict()

        for key, entity in simulation.entities.items():
            if entity.is_person:
                entity.count = entity.step_size = len(input_data_frame)
            else:
                entity.count = entity.step_size = \
                    (input_data_frame[role_variable_by_entity_key[key]] == 0).sum()
                entity.roles_count = int(input_data_frame[role_variable_by_entity_key[key]].max() + 1)
                assert isinstance(entity.roles_count, int), '{} is not a valid roles_count (int) for {}'.format(
                    entity.roles_count, entity.key)
                unique_ids_count = len(input_data_frame[id_variable_by_entity_key[key]].unique())
                assert entity.count == unique_ids_count, \
                    "There are {0} person of role 0 in {1} but {2} {1}".format(
                        entity.count, entity.key, unique_ids_count)

                entity.members_entity_id = input_data_frame[id_variable_by_entity_key[key]].astype('int').values
                entity.members_legacy_role = input_data_frame[role_variable_by_entity_key[key]].astype('int').values
                index_by_entity_key[entity.key] = input_data_frame.loc[
                    input_data_frame[role_variable_by_entity_key[entity.key]] == 0,
                    id_variable_by_entity_key[key]
                    ].sort_values().index

        for column_name, column_serie in input_data_frame.items():
            if role_variable_by_entity_key is not None:
                if column_name in role_variable_by_entity_key.values():
                    continue

            if id_variable_by_entity_key is not None:
                if column_name in id_variable_by_entity_key.values():
                    continue

            entity = simulation.get_variable_entity(column_name)
            if entity.is_person:
                init_variable_in_entity(entity, column_name, column_serie, period)
            else:
                init_variable_in_entity(entity, column_name, column_serie[index_by_entity_key[entity.key]], period)

    def new_simulation(self, debug = False, use_baseline = False, trace = False, data = None, memory_config = None):
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
        simulation = simulations.Simulation(
            debug = debug,
            opt_out_cache = True if self.cache_blacklist is not None else False,
            period = period,
            tax_benefit_system = tax_benefit_system,
            trace = trace,
            memory_config = memory_config
            )
        self.init_simulation(simulation = simulation, period = period, data = data)
        #
        if not use_baseline:
            self.simulation = simulation
        else:
            self.baseline_simulation = simulation
        #
        if 'custom_initialize' in dir(self):
            self.custom_initialize(simulation)
        #
        return simulation

    def init_simulation(self, simulation, period, data = None):

        assert data is not None
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
            self.init_all_entities(
                input_data_frame = source,
                simulation = simulation,
                period = period,
                )

        if source_type == 'input_data_table':
            # Case 1: fill simulation with a unique input_data_frame given by the attribute
            if input_data_survey_prefix is not None:
                openfisca_survey_collection = SurveyCollection.load(collection = self.collection)
                openfisca_survey = openfisca_survey_collection.get_survey("{}_{}".format(
                    input_data_survey_prefix, data_year))
                input_data_frame = openfisca_survey.get_values(table = "input").reset_index(drop = True)
            else:
                NotImplementedError

            # input_data_frame = self.input_data_frame.copy()
            self.custom_input_data_frame(input_data_frame, period = period)
            self.init_all_entities(input_data_frame, simulation, period)  # monolithic dataframes

        elif source_type == 'input_data_table_by_period':
            # Case 2: fill simulation with input_data_frame by period containing all entity variables
            for period, table in self.input_data_table_by_period.items():
                period = periods.period(period)
                log.debug('From survey {} loading table {}'.format(survey, table))
                input_data_frame = self.load_table(survey = survey, table = table)
                self.custom_input_data_frame(input_data_frame, period = period)
                self.init_all_entities(input_data_frame, simulation, period)  # monolithic dataframes

        elif source_type == 'input_data_frame_by_entity_by_period':
            for period, input_data_frame_by_entity in source.items():
                for entity in simulation.tax_benefit_system.entities:
                    input_data_frame = input_data_frame_by_entity.get(entity.key)
                    if input_data_frame is None:
                        continue
                    self.init_entity(
                        entity = entity.key,
                        input_data_frame = input_data_frame,
                        period = period,
                        simulation = simulation,
                        )

        elif source_type == 'input_data_table_by_entity_by_period':
            # Case 3: fill simulation with input_data_table by entity_by_period containing a dictionnary
            # of all periods containing a dictionnary of entity variables
            input_data_table_by_entity_by_period = source
            for period, input_data_table_by_entity in input_data_table_by_entity_by_period.items():
                period = periods.period(period)
                for entity, table in input_data_table_by_entity.items():
                    survey = 'input'
                    input_data_frame = self.load_table(survey = survey, table = table)
                    self.custom_input_data_frame(input_data_frame, period = period, entity = entity)
                    self.init_entity(
                        entity = entity,
                        input_data_frame = input_data_frame,
                        period = period,
                        simulation = simulation,
                        )
        else:
            pass

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
        """
        Neutralizing input variables not in input dataframe and keep some crucial variables
        """
        for variable_name, variable in tax_benefit_system.variables.items():
            if variable.formulas:
                continue
            if self.used_as_input_variables and (variable_name in self.used_as_input_variables):
                continue
            if self.non_neutralizable_variables and (variable_name in self.non_neutralizable_variables):
                continue
            if self.weight_column_name_by_entity and (variable_name in self.weight_column_name_by_entity.values()):
                continue

            tax_benefit_system.neutralize_variable(variable_name)

    def restore_simulations(self, directory, **kwargs):
        assert os.path.exists(directory), "Cannot restore simulations from non existent directory"

        for use_baseline in [False, True]:
            if os.path.exists(os.path.join(directory, 'baseline')):
                sub_directory = 'baseline' if use_baseline else 'reform'
                directory = os.path.join(directory, sub_directory)
            elif use_baseline:
                continue

            self._restore_simulation(directory = directory, use_baseline = use_baseline, **kwargs)

    def set_input_data_frame(self, input_data_frame):
        self.input_data_frame = input_data_frame

    def set_tax_benefit_systems(self, tax_benefit_system = None, baseline_tax_benefit_system = None):
        """
        Set the tax and benefit system and eventually the baseline tax and benefit system
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
        if use_baseline:
            simulation = self.baseline_simulation
        else:
            simulation = self.simulation

        tax_benefit_system = simulation.tax_benefit_system
        assert variable in tax_benefit_system.variables
        column = tax_benefit_system.variables[variable]

        if weighted:
            weight_variable = self.weight_column_name_by_entity[column.entity.key]
            weights = simulation.calculate(weight_variable, simulation.period)

        default_value = column.default_value
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
            infos['dtype'],
            default_value,
            humanize.naturalsize(infos['total_nb_bytes'], gnu = True),
            )
        print("")
        print(header_line)
        print("Details: ")
        holder = simulation.get_holder(variable)
        if holder is not None:
            if holder.variable.definition_period == ETERNITY:
                array = holder.get_array(ETERNITY)
                print("permanent: mean = {}, min = {}, max = {}, median = {}, default = {:.1%}".format(
                    array.mean() if not weighted else np.average(array, weights = weights),
                    array.min(),
                    array.max(),
                    np.median(array),
                    (
                        (array == default_value).sum() / len(array)
                        if not weighted
                        else ((array == default_value) * weights).sum() / weights.sum()
                        )
                    ))
            else:
                for period in sorted(holder.get_known_periods()):
                    array = holder.get_array(period)
                    if array.shape == ():
                        print("{}: always = {}".format(period, array))
                        continue

                    print("{}: mean = {}, min = {}, max = {}, mass = {:.2e}, default = {:.1%}, median = {}".format(
                        period,
                        array.mean() if not weighted else np.average(array, weights = weights),
                        array.min(),
                        array.max(),
                        array.sum() if not weighted else np.sum(array * weights),
                        (
                            (array == default_value).sum() / len(array)
                            if not weighted
                            else ((array == default_value) * weights).sum() / weights.sum()
                            ),
                        np.median(array),
                        ))

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

    def _set_ids_and_roles_variables(self):
        id_variable_by_entity_key = self.id_variable_by_entity_key
        role_variable_by_entity_key = self.role_variable_by_entity_key

        if id_variable_by_entity_key is None:
            log.debug("Use default id_variable names")
            self.id_variable_by_entity_key = dict(
                (entity.key, entity.key + '_id') for entity in self.tax_benefit_system.entities
                )
        if role_variable_by_entity_key is None:
            self.role_variable_by_entity_key = dict(
                (entity.key, entity.key + '_legacy_role') for entity in self.tax_benefit_system.entities
                )


    def _set_used_as_input_variables_by_entity(self):
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
                if tax_benefit_system.get_variable(variable).entity == entity
                ]

# Helpers

def get_words(text):
    return re.compile('[A-Za-z_]+').findall(text)


def assert_variables_in_same_entity(survey_scenario, variables):
    entity = None
    for variable_name in variables:
        variable = survey_scenario.tax_benefit_system.variables.get(variable_name)
        assert variable
        if entity is None:
            entity = variable.entity
        assert variable.entity == entity, "{} are not from the same entity: {} doesn't belong to {}".format(
            variables, variable_name, entity.key)
    return entity.key


def get_entity(survey_scenario, variable):
    variable_ = survey_scenario.tax_benefit_system.variables.get(variable)
    assert variable_, 'Variable {} is not part of the tax-benefit-system'.format(variable)
    return variable_.entity


def get_weights(survey_scenario, variable):
    entity = get_entity(survey_scenario, variable)
    weight_variable = survey_scenario.weight_column_name_by_entity.get(entity.key)
    return weight_variable


def init_variable_in_entity(entity, variable_name, series, period):
    # holder = entity.get_holder(variable)
    simulation = entity.simulation
    variable = simulation.tax_benefit_system.variables[variable_name]
    if series.values.dtype != variable.dtype:
        log.debug(
            'Converting {} from dtype {} to {}'.format(
                variable_name, series.values.dtype, variable.dtype)
            )
    if np.issubdtype(series.values.dtype, np.floating):
        if series.isnull().any():
            log.debug('There are {} NaN values for {} non NaN values in variable {}'.format(
                series.isnull().sum(), series.notnull().sum(), variable_name))
            log.debug('We convert these NaN values of variable {} to {} its default value'.format(
                variable_name, variable.default_value))
            series.fillna(variable.default_value, inplace = True)
        assert series.notnull().all(), \
            'There are {} NaN values for {} non NaN values in variable {}'.format(
                series.isnull().sum(), series.notnull().sum(), variable_name)

    array = series.values.astype(variable.dtype)
    assert array.size == entity.count, 'Entity {}: bad size for variable {} ({} instead of {})'.format(
        entity.key, variable_name, array.size, entity.count)
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
