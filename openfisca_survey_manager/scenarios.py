# -*- coding: utf-8 -*-

from __future__ import division

import humanize
import logging
import numpy as np
import pandas as pd
import re


from openfisca_core import formulas, periods, simulations
try:
    from openfisca_core.tools.memory import get_memory_usage
except ImportError:
    get_memory_usage = None
from openfisca_survey_manager.calibration import Calibration

from .survey_collections import SurveyCollection
from .surveys import Survey

log = logging.getLogger(__name__)


class AbstractSurveyScenario(object):
    filtering_variable_by_entity = None
    id_variable_by_entity_key = None
    inflator_by_variable = None  # factor used to inflate variable total
    input_data_frame = None
    input_data_table_by_period = None
    legislation_json = None
    non_neutralizable_variables = None
    cache_blacklist = None
    reference_simulation = None
    reference_tax_benefit_system = None
    role_variable_by_entity_key = None
    simulation = None
    target_by_variable = None  # variable total target to inflate to
    tax_benefit_system = None
    used_as_input_variables = None
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

    def compute_aggregate(self, variable = None, aggfunc = 'sum', filter_by = None, period = None, reference = False,
                          missing_variable_default_value = np.nan):
        # TODO deal here with filter_by instead of openfisca_france_data ?
        assert aggfunc in ['count', 'mean', 'sum']
        tax_benefit_system = self.tax_benefit_system
        if filter_by is None and self.filtering_variable_by_entity is not None:
            entity_key = tax_benefit_system.column_by_name[variable].entity.key
            filter_by = self.filtering_variable_by_entity.get(entity_key)

        assert variable is not None
        if reference:
            simulation = self.reference_simulation
        else:
            simulation = self.simulation

        assert simulation is not None

        if filter_by:
            assert filter_by in self.tax_benefit_system.column_by_name, \
                "{} is not a variables of the tax benefit system".format(filter_by)

        if self.weight_column_name_by_entity:
            weight_column_name_by_entity = self.weight_column_name_by_entity
            entity_key = tax_benefit_system.column_by_name[variable].entity.key
            entity_weight = weight_column_name_by_entity[entity_key]
        else:
            entity_weight = None

        if variable in simulation.tax_benefit_system.column_by_name:
            value = simulation.calculate_add(variable, period = period)
        else:
            log.info("Variable {} not found. Assiging {}".format(variable, missing_variable_default_value))
            return missing_variable_default_value

        weight = (
            simulation.calculate_add(entity_weight, period = period).astype(float)
            if entity_weight else 1.0
            )
        filter_dummy = simulation.calculate_add(filter_by, period = period) if filter_by else 1.0

        if aggfunc == 'sum':
            return (value * weight * filter_dummy).sum()
        elif aggfunc == 'mean':
            return (value * weight * filter_dummy).sum() / (weight * filter_dummy).sum()
        elif aggfunc == 'count':
            return (weight * filter_dummy).sum()

    def compute_pivot_table(self, aggfunc = 'mean', columns = None, difference = False, filter_by = None, index = None,
            period = None, reference = False, values = None, missing_variable_default_value = np.nan):
        assert aggfunc in ['count', 'mean', 'sum']
        assert columns or index or values
        assert not (difference and reference), "Can't have difference and reference both set to True"

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
                entity_key = tax_benefit_system.column_by_name[axe[0]].entity.key

        if filter_by is None and self.filtering_variable_by_entity is not None:
            filter_by = self.filtering_variable_by_entity.get(entity_key)

        variables = set(index + values + columns)
        # Select the entity weight corresponding to the variables that will provide values
        if self.weight_column_name_by_entity is not None:
            weight = self.weight_column_name_by_entity[entity_key]
            variables.add(weight)
        else:
            weight = None

        if filter_by is not None:
            variables.add(filter_by)
        else:
            filter_dummy = 1.0

        for variable in variables:
            assert tax_benefit_system.column_by_name[variable].entity.key == entity_key, \
                'The variable {} is not present or does not belong to entity {}'.format(
                    variable,
                    entity_key,
                    )

        if difference:
            data_frame = (
                self.create_data_frame_by_entity(
                    values, period = period, reference = False, index = False)[entity_key] -
                self.create_data_frame_by_entity(
                    values, period = period, reference = True, index = False)[entity_key]
                )
        else:
            data_frame = (
                self.create_data_frame_by_entity(
                    values, period = period, reference = reference, index = False)[entity_key]
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
                    variables = reference_variables, period = period, reference = True, index = False
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
                    result = (pivot_sum / pivot_mass)
                elif aggfunc == 'sum':
                    result = pivot_sum
                elif aggfunc == 'count':
                    result = pivot_mass

                data_frame_by_value[value] = result

            if len(data_frame_by_value.keys()) > 1:
                return data_frame_by_value
            else:
                return data_frame_by_value.values()[0]

        else:
            assert aggfunc == 'count', "Can only use count for aggfunc if no values"
            return data_frame.pivot_table(index = index, columns = columns, values = weight, aggfunc = 'sum')

    def create_data_frame_by_entity(self, variables = None, expressions = None, filter_by = None, index = False,
            period = None, reference = False, merge = False, ignore_missing_variables = False):

        simulation = self.reference_simulation if reference else self.simulation
        tax_benefit_system = self.reference_tax_benefit_system if reference else self.tax_benefit_system

        assert variables or index or expressions or filter_by

        if merge:
            index = True
        if expressions is None:
            expressions = []

        if filter_by is not None:
            if filter_by in tax_benefit_system.column_by_name.keys():
                variables.append(filter_by)
                filter_entity_key = tax_benefit_system.column_by_name.get(filter_by).entity.key
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

        missing_variables = set(variables).difference(set(tax_benefit_system.column_by_name.keys()))
        if missing_variables:
            log.info("These variables aren't par of the tax-benefit system: {}".format(missing_variables))
        columns_to_fetch = [
            tax_benefit_system.column_by_name.get(variable_name) for variable_name in variables
            if tax_benefit_system.column_by_name.get(variable_name) is not None
            ]

        assert len(columns_to_fetch) >= 1, "None of the requested variables {} are in the tax-benefit-system".format(
            variables)

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
                    (column_name, simulation.calculate_add(column_name, period = period))
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

        for entity_key, expressions in expressions_by_entity_key.iteritems():
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
            for entity_key, openfisca_data_frame in openfisca_data_frame_by_entity_key.iteritems():
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
        for entity_key, data_frame in openfisca_data_frame_by_entity.iteritems():
            survey = Survey(name = survey_name)
            survey.insert_table(name = entity_key, data_frame = data_frame)
            survey_collection.surveys.append(survey)
            survey_collection.dump(collection = "openfisca")

    def fill(self, input_data_frame, simulation, period):
        assert period is not None
        log.info('Initialasing simulation using data_frame for period {}'.format(period))
        if period.unit == 'year':  # 1. year
            self.init_simulation_with_data_frame(
                input_data_frame = input_data_frame,
                period = period,
                simulation = simulation,
                )
        elif period.unit == 'month' and period.size == 3:  # 2. quarter
            for offset in range(period.size):
                period_item = periods.period('month', period.start.offset(offset, 'month'))
                self.init_simulation_with_data_frame(
                    input_data_frame = input_data_frame,
                    period = period_item,
                    simulation = simulation,
                    )
        elif period.unit == 'month' and period.size == 1:  # 3. months
            self.init_simulation_with_data_frame(
                input_data_frame = input_data_frame,
                period = period,
                simulation = simulation,
                )
        else:
            log.info("Invalid period {}".format(period))
            raise

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
        column_by_name = tax_benefit_system.column_by_name

        id_variables = [
            id_variable_by_entity_key[entity.key] for entity in simulation.entities.values()
            if not entity.is_person]
        role_variables = [
            role_variable_by_entity_key[entity.key] for entity in simulation.entities.values()
            if not entity.is_person]

        log.debug('Variable used_as_input_variables in filter: \n {}'.format(used_as_input_variables))

        unknown_columns = []
        for column_name in input_data_frame:
            if column_name in id_variables + role_variables:
                continue
            if column_name not in column_by_name:
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
            column = column_by_name[column_name]
            formula_class = column.formula_class
            if not issubclass(formula_class, formulas.SimpleFormula):
                continue
            function = formula_class.function
            # Keeping the calculated variables that are initialized by the input data
            if function is not None:
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

    def inflate(self, inflator_by_variable = None, target_by_variable = None):
        assert inflator_by_variable or target_by_variable
        inflator_by_variable = dict() if inflator_by_variable is None else inflator_by_variable
        target_by_variable = dict() if target_by_variable is None else target_by_variable
        self.inflator_by_variable = inflator_by_variable
        self.target_by_variable = target_by_variable

        assert self.simulation is not None
        for reference in [False, True]:
            if reference is True:
                simulation = self.reference_simulation
            else:
                simulation = self.simulation
            if simulation is None:
                continue
            tax_benefit_system = self.tax_benefit_system
            for column_name in set(inflator_by_variable.keys()).union(set(target_by_variable.keys())):
                assert column_name in tax_benefit_system.column_by_name, \
                    "Variable {} is not a valid variable of the tax-benefit system".format(column_name)
                holder = simulation.get_or_new_holder(column_name)
                if column_name in target_by_variable:
                    inflator = inflator_by_variable[column_name] = \
                        target_by_variable[column_name] / self.compute_aggregate(
                            variable = column_name, reference = reference)
                    log.info('Using {} as inflator for {} to reach the target {} '.format(
                        inflator, column_name, target_by_variable[column_name]))
                else:
                    assert column_name in inflator_by_variable, 'column_name is not in inflator_by_variable'
                    log.info('Using inflator {} for {}.  The target is thus {}'.format(
                        inflator_by_variable[column_name],
                        column_name, inflator_by_variable[column_name] * self.compute_aggregate(variable = column_name))
                        )
                    inflator = inflator_by_variable[column_name]

                holder.array = inflator * holder.array

    def init_from_data_frame(self, input_data_frame = None, input_data_table_by_period = None):

        if input_data_frame is not None:
            self.set_input_data_frame(input_data_frame)

        self.input_data_table_by_period = self.input_data_table_by_period or input_data_table_by_period

        assert (
            self.input_data_frame is not None or
            self.input_data_table_by_period is not None
            )

        if self.used_as_input_variables is None:
            self.used_as_input_variables = []
        else:
            assert isinstance(self.used_as_input_variables, list)

        if 'initialize_weights' in dir(self):
            self.initialize_weights()
        #
        return self

    def init_simulation_with_data_frame(self, input_data_frame = None, period = None, simulation = None):
        """
        Initialize the simulation period with current input_data_frame
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
            id_variable_by_entity_key[entity.key] for entity in simulation.entities.values()
            if not entity.is_person]
        role_variables = [
            role_variable_by_entity_key[entity.key] for entity in simulation.entities.values()
            if not entity.is_person]

        for id_variable in id_variables + role_variables:
            assert id_variable in input_data_frame.columns, \
                "Variable {} is not present in input dataframe".format(id_variable)

        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame, simulation = simulation)

        for key, entity in simulation.entities.iteritems():
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

        for column_name, column_serie in input_data_frame.iteritems():
            if column_name in role_variable_by_entity_key.values() + id_variable_by_entity_key.values():
                continue
            holder = simulation.get_or_new_holder(column_name)
            entity = holder.entity
            if column_serie.values.dtype != holder.column.dtype:
                log.debug(
                    'Converting {} from dtype {} to {}'.format(
                        column_name, column_serie.values.dtype, holder.column.dtype)
                    )
            if np.issubdtype(column_serie.values.dtype, np.float):
                if column_serie.isnull().any():
                    log.debug('There are {} NaN values for {} non NaN values in variable {}'.format(
                        column_serie.isnull().sum(), column_serie.notnull().sum(), column_name))
                    log.debug('We convert these NaN values of variable {} to {} its default value'.format(
                        column_name, holder.column.default))
                    input_data_frame.loc[column_serie.isnull(), column_name] = holder.column.default
                assert input_data_frame[column_name].notnull().all(), \
                    'There are {} NaN values for {} non NaN values in variable {}'.format(
                        column_serie.isnull().sum(), column_serie.notnull().sum(), column_name)

            if entity.is_person:
                array = column_serie.values.astype(holder.column.dtype)
            else:
                array = column_serie.values[
                    input_data_frame[role_variable_by_entity_key[entity.key]].values == 0
                    ].astype(holder.column.dtype)
            assert array.size == entity.count, 'Bad size for {}: {} instead of {}'.format(
                column_name, array.size, entity.count)

            holder.set_input(period, np.array(array, dtype = holder.column.dtype))

    # @property
    # def input_data_frame(self):
    #     return self.input_data_frame_by_entity.get(period = periods.period(self.year))

    def new_simulation(self, debug = False, debug_all = False, reference = False, trace = False, survey = None):
        assert self.tax_benefit_system is not None
        tax_benefit_system = self.tax_benefit_system
        if self.reference_tax_benefit_system is not None and reference:
            tax_benefit_system = self.reference_tax_benefit_system
        elif reference:
            while True:
                reference_tax_benefit_system = tax_benefit_system.reference
                if isinstance(reference, bool) and reference_tax_benefit_system is None \
                        or reference_tax_benefit_system == reference:
                    break
                tax_benefit_system = reference_tax_benefit_system

        period = periods.period(self.year)
        self.neutralize_variables(tax_benefit_system)

        simulation = simulations.Simulation(
            debug = debug,
            debug_all = debug_all,
            opt_out_cache = True if self.cache_blacklist is not None else False,
            period = period,
            tax_benefit_system = tax_benefit_system,
            trace = trace,
            )
        # Case 1: fill simulation with a unique input_data_frame given by the attribute
        if self.input_data_frame is not None:
            input_data_frame = self.input_data_frame.copy()
            self.custom_input_data_frame(input_data_frame, period = period)
            self.fill(input_data_frame, simulation, period)
        # Case 2: fill simulation with input_data_frame by period containing all entity variables
        elif self.input_data_table_by_period is not None:
            for period, table in self.input_data_table_by_period.iteritems():
                period = periods.period(period)
                input_data_frame = self.load_table(survey = survey, table = table)
                self.custom_input_data_frame(input_data_frame, period = period)
                self.fill(input_data_frame, simulation, period)
        #
        if not reference:
            self.simulation = simulation
        else:
            self.reference_simulation = simulation
        #
        if 'custom_initialize' in dir(self):
            self.custom_initialize(simulation)
        #
        return simulation

    def load_table(self, variables = None, collection = None, survey = None,
            table = None):
        collection = collection or self.collection
        survey_collection = SurveyCollection.load(collection = self.collection)
        survey = survey or "{}_{}".format(self.input_data_survey_prefix, self.year)
        survey_ = survey_collection.get_survey(survey)
        log.info("Loading table {} in survey {} from collection {}".format(table, survey, collection))
        return survey_.get_values(table = table, variables = variables)

    def memory_usage(self, reference = False):
        if reference:
            simulation = self.reference_simulation
        else:
            simulation = self.simulation

        infos_by_variable = get_memory_usage(simulation)
        infos_lines = list()
        for variable, infos in infos_by_variable.iteritems():
            hits = infos.get('hits', (None, None))
            infos_lines.append((infos['nbytes'], variable, "{}: {} periods * {} cells * item size {} ({}) = {} with {} hits (missed = {})".format(
                variable,
                len(infos['periods']),
                infos['ncells'],
                infos['item_size'],
                infos['dtype'],
                humanize.naturalsize(infos['nbytes'], gnu = True),
                hits[0],
                hits[1],
                )))
        infos_lines.sort()
        for _, _, line in infos_lines:
            print(line.rjust(100))

    def neutralize_variables(self, tax_benefit_system):
        """
        Neutralizing input variables not present in the input_data_frame and keep some crucial variables
        """
        for column_name, column in tax_benefit_system.column_by_name.items():
            formula_class = column.formula_class
            if not issubclass(formula_class, formulas.SimpleFormula):
                continue
            function = formula_class.function
            if function is not None:
                continue
            if column_name in self.used_as_input_variables:
                continue
            if self.non_neutralizable_variables and (column_name in self.non_neutralizable_variables):
                continue
            if self.weight_column_name_by_entity and column_name in self.weight_column_name_by_entity.values():
                continue

            tax_benefit_system.neutralize_column(column_name)

    def set_input_data_frame(self, input_data_frame):
        self.input_data_frame = input_data_frame

    def set_tax_benefit_systems(self, tax_benefit_system = None, reference_tax_benefit_system = None):
        """
        Set the tax and benefit system and eventually the reference atx and benefit system
        """
        assert tax_benefit_system is not None
        self.tax_benefit_system = tax_benefit_system
        if self.cache_blacklist is not None:
            self.tax_benefit_system.cache_blacklist = self.cache_blacklist
        if reference_tax_benefit_system is not None:
            self.reference_tax_benefit_system = reference_tax_benefit_system
            if self.cache_blacklist is not None:
                self.reference_tax_benefit_system.cache_blacklist = self.cache_blacklist

    def summarize_variable(self, variable = None, reference = False, weighted = False, force_compute = False):
        if reference:
            simulation = self.reference_simulation
        else:
            simulation = self.simulation

        tax_benefit_system = simulation.tax_benefit_system
        assert variable in tax_benefit_system.column_by_name.keys()
        column = tax_benefit_system.column_by_name[variable]

        if weighted:
            weight_variable = self.weight_column_name_by_entity[column.entity.key]
            weights = simulation.calculate(weight_variable)

        default_value = column.default
        infos_by_variable = get_memory_usage(simulation, variables = [variable])

        if not infos_by_variable:
            if force_compute:
                simulation.calculate_add(variable)
                self.summarize_variable(variable = variable, reference = reference, weighted = weighted)
                return
            else:
                print("{} is not computed yet. Use keyword argument force_compute = True".format(variable))
                return
        infos = infos_by_variable[variable]
        header_line = "{}: {} periods * {} cells * item size {} ({}, default = {}) = {}".format(
            variable,
            len(infos['periods']),
            infos['ncells'],
            infos['item_size'],
            infos['dtype'],
            default_value,
            humanize.naturalsize(infos['nbytes'], gnu = True),
            )
        print("")
        print(header_line)
        print("Details: ")
        holder = simulation.holder_by_name[variable]
        if holder is not None:
            if holder._array is not None:
                # Only used when column.is_permanent
                array = holder._array
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
            elif holder._array_by_period is not None:
                for period in sorted(holder._array_by_period.keys()):
                    array = holder._array_by_period[period]
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


# Helpers

# TODO NOT WORKING RIGH NOW
def init_simulation_with_data_frame_by_entity(input_data_frame_by_entity = None, simulation = None):
    assert input_data_frame_by_entity is not None
    assert simulation is not None
    for entity in simulation.entities.values():
        if entity.index_for_person_variable_name is not None:
            input_data_frame = input_data_frame_by_entity[entity.index_for_person_variable_name]
        else:
            input_data_frame = input_data_frame_by_entity['individus']
        input_data_frame = filter_input_variables(input_data_frame)

        if entity.is_persons_entity:
            entity.count = entity.step_size = len(input_data_frame)
        else:
            entity.count = entity.step_size = len(input_data_frame)
            entity.roles_count = input_data_frame_by_entity['individus'][
                entity.role_for_person_variable_name].max() + 1
            assert isinstance(entity.roles_count, int)

        # Convert columns from df to array:
        for column_name, column_serie in input_data_frame.iteritems():
            holder = simulation.get_or_new_holder(column_name)
            entity = holder.entity
            if column_serie.values.dtype != holder.column.dtype:
                log.debug(
                    'Converting {} from dtype {} to {}'.format(
                        column_name, column_serie.values.dtype, holder.column.dtype)
                    )
            if np.issubdtype(column_serie.values.dtype, np.float):
                assert column_serie.notnull().all(), 'There are {} NaN values in variable {}'.format(
                    column_serie.isnull().sum(), column_name)

            array = column_serie.values.astype(holder.column.dtype)
            assert array.size == entity.count, 'Bad size for {}: {} instead of {}'.format(
                column_name,
                array.size,
                entity.count)
            holder.array = np.array(array, dtype = holder.column.dtype)


# Helpers

def get_words(text):
    return re.compile('[A-Za-z_]+').findall(text)


def assert_variables_in_same_entity(survey_scenario, variables):
    entity = None
    for variable_name in variables:
        variable = survey_scenario.tax_benefit_system.column_by_name.get(variable_name)
        assert variable
        if entity is None:
            entity = variable.entity
        assert variable.entity == entity, "{} are not from the same entity: {} doesn't belong to {}".format(
            variables, variable_name, entity.key)
    return entity.key


def get_entity(survey_scenario, variable):
    variable_ = survey_scenario.tax_benefit_system.column_by_name.get(variable)
    assert variable_, 'Variable {} is not part of the tax-benefit-system'.format(variable)
    return variable_.entity


def get_weights(survey_scenario, variable):
    entity = get_entity(survey_scenario, variable)
    weight_variable = survey_scenario.weight_column_name_by_entity.get(entity.key)
    return weight_variable
