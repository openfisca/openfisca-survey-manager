# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging
import numpy as np
import pandas

from openfisca_core import periods, simulations
from .surveys import Survey

log = logging.getLogger(__name__)


class AbstractSurveyScenario(object):
    inflator_by_variable = None  # factor used to inflate variable total
    input_data_frame = None
    input_data_frames_by_entity_key_plural = None
    legislation_json = None
    reform = None
    simulation = None
    tax_benefit_system = None
    target_by_variable = None  # variable total target to inflate to
    used_as_input_variables = None
    year = None
    weight_column_name_by_entity_key_plural = dict()

    def init_from_data_frame(self, input_data_frame = None, input_data_frames_by_entity_key_plural = None,
            reform = None, tax_benefit_system = None, used_as_input_variables = None, year = None):
        assert input_data_frame is not None or input_data_frames_by_entity_key_plural is not None

        if input_data_frame is not None:
            self.input_data_frame = input_data_frame
        elif input_data_frames_by_entity_key_plural is not None:
            self.input_data_frames_by_entity_key_plural = input_data_frames_by_entity_key_plural

        if used_as_input_variables is None:
            self.used_as_input_variables = []
        else:
            assert isinstance(used_as_input_variables, list)
            self.used_as_input_variables = used_as_input_variables
        assert tax_benefit_system is not None
        self.tax_benefit_system = tax_benefit_system
        self.reform = reform
        assert year is not None
        self.year = year
        return self

    def inflate(self, inflator_by_variable = dict(), target_by_variable = dict()):
        assert inflator_by_variable or target_by_variable
        assert self.simulation is not None
        simulation = self.simulation
        self.inflator_by_variable = inflator_by_variable
        self.target_by_variable = target_by_variable
        tax_benefit_system = self.tax_benefit_system
        for column_name in set(inflator_by_variable.keys()).union(set(target_by_variable.keys())):
            assert column_name in tax_benefit_system.column_by_name
            holder = simulation.get_or_new_holder(column_name)

            if column_name in target_by_variable:
                log.info('Computing inflator for {} to reach the target {}'.format(
                    column_name, target_by_variable[column_name]))

                inflator = inflator_by_variable[column_name] = \
                    target_by_variable[column_name] / compute_aggregate(self, variable = column_name)
                continue
            else:
                log.info('Using inflator {} for {}.  The target {}'.format(
                    inflator_by_variable[column_name]), column_name, compute_aggregate(self, variable = column_name))
                inflator = inflator_by_variable[column_name]
            holder.array = inflator * holder.array

    def new_simulation(self, debug = False, debug_all = False, reference = False, trace = False):
        assert isinstance(reference, (bool, int)), \
            'Parameter reference must be a boolean. When True, the reference tax-benefit system is used.'
        assert self.tax_benefit_system is not None
        tax_benefit_system = self.tax_benefit_system
        if reference:
            while True:
                reference_tax_benefit_system = tax_benefit_system.reference
                if reference_tax_benefit_system is None:
                    break
                tax_benefit_system = reference_tax_benefit_system
        simulation = simulations.Simulation(
            debug = debug,
            debug_all = debug_all,
            period = periods.period(self.year),
            tax_benefit_system = tax_benefit_system,
            trace = trace,
            )

        id_variables = [
            entity.index_for_person_variable_name for entity in simulation.entity_by_key_singular.values()
            if not entity.is_persons_entity]

        role_variables = [
            entity.role_for_person_variable_name for entity in simulation.entity_by_key_singular.values()
            if not entity.is_persons_entity]

        column_by_name = tax_benefit_system.column_by_name
        used_as_input_variables = self.used_as_input_variables

        # Define a useful function to clean the data_frame
        def filter_input_variables(input_data_frame):
            for column_name in input_data_frame:
                if column_name not in column_by_name:
                    log.info('Unknown column "{}" in survey, dropped from input table'.format(column_name))
                    # waiting for the new pandas version to hit Travis repo
                    input_data_frame = input_data_frame.drop(column_name, axis = 1)
                    # , inplace = True)  # TODO: effet de bords ?

            for column_name in input_data_frame:
                if column_name in id_variables + role_variables:
                    continue
                if column_by_name[column_name].formula_class.function is not None:
                    if column_name in used_as_input_variables:
                        log.info(
                            'Column "{}" not dropped because present in used_as_input_variables'.format(column_name))
                        continue

                    log.info('Column "{}" in survey set to be calculated, dropped from input table'.format(column_name))
                    input_data_frame = input_data_frame.drop(column_name, axis = 1)
                    # , inplace = True)  # TODO: effet de bords ?
            return input_data_frame

        assert self.input_data_frame is not None or self.input_data_frames_by_entity_key_plural is not None
        input_data_frame = self.input_data_frame
        input_data_frames_by_entity_key_plural = self.input_data_frames_by_entity_key_plural

        # Case 1: fill simulation with a unique input_data_frame containing all entity variables
        if input_data_frame is not None:
            for id_variable in id_variables + role_variables:
                assert id_variable in input_data_frame.columns, \
                    "Variable {} is not present in input dataframe".format(id_variable)

            input_data_frame = filter_input_variables(input_data_frame)

            for entity in simulation.entity_by_key_singular.values():
                if entity.is_persons_entity:
                    entity.count = entity.step_size = len(input_data_frame)
                else:
                    entity.count = entity.step_size = \
                        (input_data_frame[entity.role_for_person_variable_name] == 0).sum()
                    entity.roles_count = input_data_frame[entity.role_for_person_variable_name].max() + 1

            for column_name, column_serie in input_data_frame.iteritems():
                holder = simulation.get_or_new_holder(column_name)
                entity = holder.entity
                if column_serie.values.dtype != holder.column.dtype:
                    log.info(
                        'Converting {} from dtype {} to {}'.format(
                            column_name, column_serie.values.dtype, holder.column.dtype)
                        )
                if entity.is_persons_entity:
                        array = column_serie.values.astype(holder.column.dtype)
                else:
                    array = column_serie.values[
                        input_data_frame[entity.role_for_person_variable_name].values == 0
                        ].astype(holder.column.dtype)
                assert array.size == entity.count, 'Bad size for {}: {} instead of {}'.format(
                    column_name,
                    array.size,
                    entity.count)
                holder.array = np.array(array, dtype = holder.column.dtype)

        # Case 2: fill simulation with an input_data_frame by entity
        elif input_data_frames_by_entity_key_plural is not None:

            for entity in simulation.entity_by_key_singular.values():
                if entity.index_for_person_variable_name is not None:
                    input_data_frame = input_data_frames_by_entity_key_plural[entity.index_for_person_variable_name]
                else:
                    input_data_frame = input_data_frames_by_entity_key_plural['individus']
                input_data_frame = filter_input_variables(input_data_frame)

                if entity.is_persons_entity:
                    entity.count = entity.step_size = len(input_data_frame)
                else:
                    entity.count = entity.step_size = len(input_data_frame)
                    entity.roles_count = input_data_frames_by_entity_key_plural['individus'][entity.role_for_person_variable_name].max() + 1

                # Convert columns from df to array:
                for column_name, column_serie in input_data_frame.iteritems():
                    holder = simulation.get_or_new_holder(column_name)
                    entity = holder.entity
                    if column_serie.values.dtype != holder.column.dtype:
                        log.info(
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

        self.simulation = simulation
        if 'initialize_weights' in dir(self):
            self.initialize_weights()
        if 'custom_initialize' in dir(self):
            self.custom_initialize()
        return simulation

    def create_data_frame_by_entity_key_plural(self, variables = None, indices = False, roles = False):
        assert variables is not None or indices or roles
        variables = list(
            set(variables).union(set(self.index_variables(indices = indices, roles = roles)))
            )
        tax_benefit_system = self.tax_benefit_system
        simulation = self.simulation
        missing_variables = set(variables).difference(set(self.tax_benefit_system.column_by_name.keys()))
        if missing_variables:
            log.info("These variables aren't par of the tax-benefit system: {}".format(missing_variables))
        columns_to_fetch = [
            self.tax_benefit_system.column_by_name.get(variable_name) for variable_name in variables
            if self.tax_benefit_system.column_by_name.get(variable_name) is not None
            ]
        openfisca_data_frame_by_entity_key_plural = dict()
        for entity_key_plural in tax_benefit_system.entity_class_by_key_plural.keys():
            column_names = [
                column.name for column in columns_to_fetch
                if column.entity_key_plural == entity_key_plural
                ]
            openfisca_data_frame_by_entity_key_plural[entity_key_plural] = pandas.DataFrame(
                dict((column_name, simulation.calculate_add(column_name)) for column_name in column_names)
                )
        return openfisca_data_frame_by_entity_key_plural

    def dump_data_frame_by_entity_key_plural(self, variables = None, survey_collection = None, survey_name = None):
        assert survey_collection is not None
        assert survey_name is not None
        assert variables is not None
        openfisca_data_frame_by_entity_key_plural = self.create_data_frame_by_entity_key_plural(variables = variables)
        for entity_key_plural, data_frame in openfisca_data_frame_by_entity_key_plural.iteritems():
            survey = Survey(name = survey_name)
            survey.insert_table(name = entity_key_plural, data_frame = data_frame)
            survey_collection.surveys.append(survey)
            survey_collection.dump(collection = "openfisca")

    def index_variables(self, indices = True, roles = True):
        variables = list()
        for entity in self.tax_benefit_system.entity_class_by_key_plural.values():
            if indices:
                variables.append(entity.index_for_person_variable_name)
            if roles:
                variables.append(entity.role_for_person_variable_name)
        return variables


# Helper

def compute_aggregate(survey_scenario = None, variable = None, period = None):
    assert survey_scenario is not None
    assert variable is not None
    assert survey_scenario.simulation is not None
    assert variable in survey_scenario.tax_benefit_system.column_by_name
    assert survey_scenario.weight_column_name_by_entity_key_plural
    simulation = survey_scenario.simulation
    tax_benefit_system = survey_scenario.tax_benefit_system
    weight_column_name_by_entity_key_plural = survey_scenario.weight_column_name_by_entity_key_plural
    entity_key_plural = tax_benefit_system.column_by_name[variable].entity_key_plural
    weight = weight_column_name_by_entity_key_plural[entity_key_plural]
    return (
        simulation.calculate_add(variable, period = period) * simulation.calculate_add(weight, period = period)
        ).sum()
