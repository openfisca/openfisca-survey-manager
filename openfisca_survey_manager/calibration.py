import logging

import numpy
from numpy import logical_not
import pandas as pd

from openfisca_core.model_api import Enum
from openfisca_survey_manager.calmar import calmar


log = logging.getLogger(__name__)


class Calibration(object):
    """An object to calibrate survey data of a SurveySimulation."""

    entity = None
    filter_by_name = None
    initial_total_population = None
    _initial_weight_name = None
    initial_weight_by_entity = dict()
    margins_by_variable = dict()
    parameters = {
        'use_proportions': True,
        'initial_weight': None,
        'method': None,  # 'linear', 'raking ratio', 'logit'
        'up': None,
        'lo': None
        }
    period = None
    survey_scenario = None
    total_population = None
    weight_name = None

    def __init__(self, survey_scenario, weight_variable_name = None):
        self.period = survey_scenario.period
        weight_variable_instance = survey_scenario.tax_benefit_system.variables.get(weight_variable_name)
        assert weight_variable_name is not None
        self.weight_name = weight_variable_name
        self._set_survey_scenario(survey_scenario)
        self.entity = weight_variable_instance.entity.key

    def reset(self):
        """Reset the calibration to its initial state."""
        simulation = self.survey_scenario.simulation
        holder = simulation.get_holder(self.weight_name)
        holder.array = numpy.array(self.initial_weight, dtype = holder.variable.dtype)

    def _set_survey_scenario(self, survey_scenario):
        """Set the survey scenario.

        Args:
          survey_scenario: the survey scenario
        """
        self.survey_scenario = survey_scenario
        weight_name = self.weight_name
        # TODO deal with baseline if reform is present
        if survey_scenario.simulation is None:
            survey_scenario.simulation = survey_scenario.new_simulation()
        period = self.period
        if self.filter_by_name:
            self.filter_by = filter_by = survey_scenario.calculate_variable(
                variable = self.filter_by_name, period = period)
        else:
            self.filter_by = filter_by = numpy.array(1.0)
        assert weight_name is not None, "A calibration needs a weight variable name to act on"
        self._initial_weight_name = weight_name + "_ini"
        self.initial_weight = initial_weight = survey_scenario.calculate_variable(
            variable = weight_name, period = period)

        self.initial_total_population = sum(initial_weight * filter_by)
        self.weight = survey_scenario.calculate_variable(variable = weight_name, period = period)

        for entity, weight_variable in survey_scenario.weight_variable_by_entity.items():
            self.initial_weight_by_entity[entity] = survey_scenario.calculate_variable(variable = weight_variable, period = period)

    def set_parameters(self, parameter, value):
        """Set a parameter value.

        Args:
          parameter: the parameter to be set
          value: the value used to set the parameter
        """
        if parameter == 'lo':
            self.parameters['lo'] = 1 / value
        else:
            self.parameters[parameter] = value

    def get_parameters(self) -> dict:
        """Get the parameters.

        Returns:
            dict: Parameters
        """
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
        p['initial_weight'] = self.weight_name + ""
        return p

    def _build_calmar_data(self) -> pd.DataFrame:
        """Build the data dictionnary used as calmar input argument.

        Returns:
            pd.DataFrame: Data used by calmar
        """
        # Select only filtered entities
        assert self._initial_weight_name is not None
        data = pd.DataFrame()
        data[self._initial_weight_name] = self.initial_weight * self.filter_by

        for variable in self.margins_by_variable:
            if variable == 'total_population':
                continue
            assert variable in self.survey_scenario.tax_benefit_system.variables
            period = self.period
            data[variable] = self.survey_scenario.calculate_variable(variable = variable, period = period)

        return data

    def _update_weights(self, margins, parameters = None):
        """Run calmar, stores new weights and returns adjusted margins.

        Args:
          margins: margins
          parameters:  Parameters (Default value = {})

        Returns:
            dict: Updated margins

        """
        if parameters is None:
            parameters = dict()

        margin_variables = list(margins.keys())
        entity = self.survey_scenario.tax_benefit_system.variables[margin_variables[0]].entity.key
        weight_variable = self.survey_scenario.weight_variable_by_entity[entity]

        if self.weight_name != weight_variable:
            raise NotImplementedError("Calmar needs to be adapted. Consider using a projected target on the entity with changing weights")

        data = self._build_calmar_data()

        assert self._initial_weight_name is not None
        parameters['initial_weight'] = self._initial_weight_name
        val_pondfin, lambdasol, updated_margins = calmar(
            data, margins, **parameters)
        # Updating only afetr filtering weights
        self.weight = val_pondfin * self.filter_by + self.weight * (logical_not(self.filter_by))
        return updated_margins

    def calibrate(self):
        """Apply the calibrations by updating weights and margins."""
        assert self.margins_by_variable is not None, "Margins by variable should be set"
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
        """Modify the weights to use the calibrated weights."""
        period = self.period
        survey_scenario = self.survey_scenario
        assert survey_scenario.simulation is not None
        for simulation in [survey_scenario.simulation, survey_scenario.baseline_simulation]:
            if simulation is None:
                continue
            simulation.set_input(self.weight_name, period, self.weight)
            for weight_name in survey_scenario.weight_variable_by_entity.values():
                if weight_name == self.weight_name:
                    continue
                # Delete other entites already computed weigths
                # to ensure that this weights a recomputed if they derive from
                # the calibrated weight variable
                weight_variable = survey_scenario.tax_benefit_system.variables[weight_name]
                if weight_variable.formulas:
                    simulation.delete_arrays(weight_variable.name, period)

    def set_target_margins(self, target_margin_by_variable: dict):
        """Set target margins.

        Args:
            target_margin_by_variable (dict): Targets margins
        """
        for variable, target in target_margin_by_variable.items():
            self.set_target_margin(variable, target)

    def set_target_margin(self, variable, target):
        """Set variable target margin.

        Args:
          variable: Target variable
          target: Target value
        """
        survey_scenario = self.survey_scenario
        period = self.period
        assert variable in survey_scenario.tax_benefit_system.variables
        variable_instance = survey_scenario.tax_benefit_system.variables[variable]

        filter_by = self.filter_by
        target_by_category = None
        categorical_variable = (
            (variable_instance.value_type in [bool, Enum])
            or (variable_instance.unit == 'years')
            or (variable_instance.unit == 'months')
            )
        if categorical_variable:
            value = survey_scenario.calculate_variable(variable = variable, period = period)
            filtered_value = value if all(filter_by) else value[filter_by.astype(bool)]
            categories = numpy.sort(numpy.unique(filtered_value))
            target_by_category = dict(zip(categories, target))

        if not self.margins_by_variable:
            self.margins_by_variable = dict()
        if variable not in self.margins_by_variable:
            self.margins_by_variable[variable] = dict()
        self.margins_by_variable[variable]['target'] = target_by_category or target
        self._update_margins()

    def _update_margins(self):
        """Update margins."""
        for variable in self.margins_by_variable:
            survey_scenario = self.survey_scenario
            period = self.period
            assert variable in survey_scenario.tax_benefit_system.variables
            variable_instance = survey_scenario.tax_benefit_system.variables[variable]

            # These are the varying weights
            weight = self.weight
            filter_by = self.filter_by
            initial_weight = self.initial_weight

            entity = variable_instance.entity.key
            value = survey_scenario.calculate_variable(variable, period = period)
            weight_variable = survey_scenario.weight_variable_by_entity[entity]

            weight = survey_scenario.calculate_variable(weight_variable, period)
            initial_weight = self.initial_weight_by_entity[entity]

            if filter_by != 1:
                if weight_variable != self.weight_name:
                    NotImplementedError("No filtering possible so far when target varaible is not on the same entity as varying weights")

                weight = weight[filter_by]
                initial_weight = initial_weight[filter_by]
                value = value[filter_by]

            margin_items = [
                ('actual', weight),
                ('initial', initial_weight),
                ]

            if variable_instance.value_type in [bool, Enum]:
                margin_items.append(('category', value))
                margins_data_frame = pd.DataFrame.from_items(margin_items)
                margins_data_frame = margins_data_frame.groupby('category', sort = True).sum()
                margin_by_type = margins_data_frame.to_dict()
            else:
                margin_by_type = dict(
                    actual = (weight * value).sum(),
                    initial = (initial_weight * value).sum(),
                    )
            self.margins_by_variable[variable].update(margin_by_type)
