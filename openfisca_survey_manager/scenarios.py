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


from openfisca_core import periods, simulations

log = logging.getLogger(__name__)


class AbstractSurveyScenario(object):
    inflators = None
    input_data_frame = None
    legislation_json = None
    simulation = None
    tax_benefit_system = None
    year = None
    weight_column_name_by_entity_key_plural = dict()

    def init_from_data_frame(
            self,
            input_data_frame = None,
            tax_benefit_system = None,
            year = None):

        assert input_data_frame is not None
        self.input_data_frame = input_data_frame
        assert tax_benefit_system is not None
        self.tax_benefit_system = tax_benefit_system
        assert year is not None
        self.year = year
        return self

    def inflate(self, inflators = None):
        if inflators is not None:
            self.inflators = inflators
        assert self.inflators is not None
        assert self.simulation is not None
        simulation = self.simulation
        tax_benefit_system = self.tax_benefit_system
        for column_name, inflator in inflators:
            assert column_name in tax_benefit_system.column_by_name
            holder = simulation.get_or_new_holder(column_name)
            holder.array = inflator * holder.array

    def new_simulation(self, debug = False, debug_all = False, trace = False):
        assert self.init_from_data_frame is not None
        assert self.tax_benefit_system is not None
        input_data_frame = self.input_data_frame
        simulation = simulations.Simulation(
            debug = debug,
            debug_all = debug_all,
            period = periods.period(self.year),
            tax_benefit_system = self.tax_benefit_system,
            trace = trace,
            )

        id_variables = [
            entity.index_for_person_variable_name for entity in simulation.entity_by_key_singular.values()
            if not entity.is_persons_entity]

        role_variables = [
            entity.role_for_person_variable_name for entity in simulation.entity_by_key_singular.values()
            if not entity.is_persons_entity]

        for id_variable in id_variables + role_variables:
            assert id_variable in self.input_data_frame.columns, \
                "Variable {} is not present in input dataframe".format(id_variable)

        column_by_name = self.tax_benefit_system.column_by_name

        for column_name in input_data_frame:
            if column_name not in column_by_name:
                log.info('Unknown column "{}" in survey, dropped from input table'.format(column_name))
                # waiting for the new pandas version to hit Travis repo
                input_data_frame = input_data_frame.drop(column_name, axis = 1)
                # , inplace = True)  # TODO: effet de bords ?

        for column_name in input_data_frame:
            if column_name in id_variables + role_variables:
                continue
            if column_by_name[column_name].formula_class is not None:
                log.info('Column "{}" in survey set to be calculated, dropped from input table'.format(column_name))
                input_data_frame = input_data_frame.drop(column_name, axis = 1)
                # , inplace = True)  # TODO: effet de bords ?

        for entity in simulation.entity_by_key_singular.values():
            if entity.is_persons_entity:
                entity.count = entity.step_size = len(input_data_frame)
            else:
                entity.count = entity.step_size = (input_data_frame[entity.role_for_person_variable_name] == 0).sum()
                entity.roles_count = input_data_frame[entity.role_for_person_variable_name].max() + 1
#       TODO: Create a validation/conversion step
#       TODO: introduce an assert when loading in place of astype
        for column_name, column_series in input_data_frame.iteritems():
            holder = simulation.get_or_new_holder(column_name)
            entity = holder.entity
            if entity.is_persons_entity:
                array = column_series.values.astype(holder.column.dtype)
            else:
                array = column_series.values[input_data_frame[entity.role_for_person_variable_name].values == 0].astype(
                    holder.column.dtype)
            assert array.size == entity.count, 'Bad size for {}: {} instead of {}'.format(
                column_name,
                array.size,
                entity.count)
            holder.array = np.array(array, dtype = holder.column.dtype)

        self.simulation = simulation
        return simulation
