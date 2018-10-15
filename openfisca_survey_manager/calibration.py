# -*- coding: utf-8 -*-


import logging

import numpy
from numpy import logical_not
from pandas import DataFrame

from openfisca_core.columns import AgeCol, BoolCol, EnumCol
from openfisca_survey_manager.calmar import calmar


log = logging.getLogger(__name__)


class Calibration(object):
    """
    An object to calibrate survey data of a SurveySimulation
    """
    filter_by_name = None
    initial_total_population = None
    margins_by_variable = dict()
    parameters = {
        'use_proportions': True,
        'pondini': None,
        'method': None,  # 'linear', 'raking ratio', 'logit'
        'up': None,
        'lo': None
        }
    survey_scenario = None
    total_population = None
    weight_name = None
    initial_weight_name = None

    def __init__(self, survey_scenario = None):
        self.filter_by_name = "menage_ordinaire"  # TODO should migrate this to france
        assert survey_scenario is not None
        self._set_survey_scenario(survey_scenario)

    def reset(self):
        """
        Reset the calibration to it initial state
        """
        simulation = self.survey_scenario.simulation
        holder = simulation.get_holder(self.weight_name)
        holder.array = numpy.array(self.initial_weight, dtype = holder.variable.dtype)

    def _set_survey_scenario(self, survey_scenario):
        """
        Set simulation
        """
        self.survey_scenario = survey_scenario
        # TODO deal with baseline if reform is present
        if survey_scenario.simulation is None:
            survey_scenario.simulation = survey_scenario.new_simulation()
        period = self.simulation.period
        self.filter_by = filter_by = survey_scenario.calculate_variable(
            variable = self.filter_by_name, period = period)
        # TODO: shoud not be france specific
        self.weight_name = weight_name = self.survey_scenario.weight_column_name_by_entity['menage']
        self.initial_weight_name = weight_name + "_ini"
        self.initial_weight = initial_weight = survey_scenario.calculate_variable(
            variable = weight_name, period = period)
        self.initial_total_population = sum(initial_weight * filter_by)
        self.weight = survey_scenario.calculate_variable(variable = weight_name, period = period)

    def set_parameters(self, parameter, value):
        """
        Set parameter
        """
        if parameter == 'lo':
            self.parameters['lo'] = 1 / value
        else:
            self.parameters[parameter] = value

#    def set_margins_target_from_file(self, filename, year, source):
#        """
#        Sets margins for inputs variable from file
#        """
#        # TODO read from h5 files
#        with open(filename) as f_tot:
#            totals = read_csv(f_tot, index_col = (0, 1))
#        # if data for the configured year is not availbale leave margins empty
#        year = str(year)
#        if year not in totals:
#            return
#        margins = {}
#        if source == "input":
#            self.input_margins_data_frame = totals.rename(columns = {year: 'target'}, inplace = False)
#        elif source == 'output':
#            self.output_margins_data_frame = totals.rename(columns = {year: 'target'}, inplace = False)
#
#        for var, mod in totals.index:
#            if var not in margins:
#                margins[var] = {}
#            margins[var][mod] = totals.get_value((var, mod), year)
#
#        for var in margins:
#            if var == 'total_population':
#                if source == "input" or source == "config":
#                    total_population = margins.pop('total_population')[0]
#                    margins['total_population'] = total_population
#                    self.total_population = total_population
#            else:
#                self.add_var2(var, margins[var], source = source)

    def get_parameters(self):
        p = {}
        p['method'] = self.parameters.get('method', 'linear')
        if self.parameters.get('invlo') is not None:
            p['lo'] = 1 / self.parameters.get('invlo')
        p['up'] = self.parameters.get('up')
        if p['method'] == 'logit':
            assert self.parameters.get('invlo') is not None and self.parameters.get('up') is not None
            p['lo'] = 1 / self.parameters.get('invlo')
            p['up'] = self.parameters.get('up')
        p['use_proportions'] = self.parameters.get('use_proportions', True)
        p['pondini'] = self.weight_name + ""
        return p

    def _build_calmar_data(self):
        """
        Builds the data dictionnary used as calmar input argument
        """
        # Select only filtered entities
        assert self.initial_weight_name is not None
        data = {self.initial_weight_name: self.initial_weight * self.filter_by}
        for variable in self.margins_by_variable:
            if variable == 'total_population':
                continue
            assert variable in self.survey_scenario.tax_benefit_system.variables
            period = self.survey_scenario.simulation.period
            data[variable] = self.survey_scenario.calculate_variable(variable = variable, period = period)

        return data

    def _update_weights(self, margins, parameters = {}):
        """
        Runs calmar, stores new weights and returns adjusted margins
        """
        data = self._build_calmar_data()
        assert self.initial_weight_name is not None
        val_pondfin, lambdasol, updated_margins = calmar(
            data, margins, parameters = parameters, pondini = self.initial_weight_name
            )
        # Updating only afetr filtering weights
        self.weight = val_pondfin * self.filter_by + self.weight * (logical_not(self.filter_by))
        return updated_margins

    def calibrate(self):
        margins_by_variable = self.margins_by_variable
        parameters = self.get_parameters()

        if margins_by_variable is not None:
            simple_margins_by_variable = dict([
                (variable, margins_by_type['target'])
                for variable, margins_by_type in margins_by_variable.items()])
        else:
            simple_margins_by_variable = dict()

        if self.total_population:
            simple_margins_by_variable['total_population'] = self.total_population

        self._update_weights(simple_margins_by_variable, parameters = parameters)
        self._update_margins()

    def set_calibrated_weights(self):
        """
        Modify the weights to use the calibrated weights
        """
        survey_scenario = self.survey_scenario
        assert survey_scenario.simulation is not None
        for simulation in [survey_scenario.simulation, survey_scenario.baseline_simulation]:
            if simulation is None:
                continue
            holder = simulation.get_holder(self.weight_name)
            holder.array = numpy.array(self.weight, dtype = holder.variable.dtype)
            # TODO: propagation to other weights

    def set_target_margins(self, target_margin_by_variable):
        for variable, target in target_margin_by_variable.items():
            self.set_target_margin(variable, target)

    def set_target_margin(self, variable, target):
        survey_scenario = self.survey_scenario
        period = survey_scenario.simulation.period
        assert variable in survey_scenario.tax_benefit_system.variables
        column = survey_scenario.tax_benefit_system.variables[variable]

        filter_by = self.filter_by
        target_by_category = None
        if column.__class__ in [AgeCol, BoolCol, EnumCol]:
            value = survey_scenario.calculate_variable(variable = variable, period = period)
            categories = numpy.sort(numpy.unique(value[filter_by]))
            target_by_category = dict(zip(categories, target))

        # assert len(atrget) = len
        if not self.margins_by_variable:
            self.margins_by_variable = dict()
        if variable not in self.margins_by_variable:
            self.margins_by_variable[variable] = dict()
        self.margins_by_variable[variable]['target'] = target_by_category or target
        self._update_margins()

    def _update_margins(self):
        for variable in self.margins_by_variable:
            survey_scenario = self.survey_scenario
            period = survey_scenario.simulation.period
            assert variable in survey_scenario.tax_benefit_system.variables
            column = survey_scenario.tax_benefit_system.variables[variable]
            weight = self.weight
            filter_by = self.filter_by
            initial_weight = self.initial_weight

            value = survey_scenario.calculate_variable(variable, period = period)
            margin_items = [
                ('actual', weight[filter_by]),
                ('initial', initial_weight[filter_by]),
                ]

            if column.__class__ in [AgeCol, BoolCol, EnumCol]:
                margin_items.append(('category', value[filter_by]))
                # TODO: should not use DataFrame for that ...
                margins_data_frame = DataFrame.from_items(margin_items)
                margins_data_frame = margins_data_frame.groupby('category', sort = True).sum()
                margin_by_type = margins_data_frame.to_dict()
            else:
                margin_by_type = dict(
                    actual = (weight[filter_by] * value[filter_by]).sum(),
                    initial = (initial_weight[filter_by] * value[filter_by]).sum(),
                    )
            self.margins_by_variable[variable].update(margin_by_type)
