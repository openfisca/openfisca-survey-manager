import logging

import numpy
from numpy import logical_not
import pandas as pd

from openfisca_core.model_api import Enum
from openfisca_survey_manager.calmar import calmar


log = logging.getLogger(__name__)


class Calibration(object):
    """An object to calibrate survey data of a SurveyScenario."""

    entity = None
    filter_by = None
    initial_entity_count = None
    _initial_weight_name = None
    initial_weight_by_entity = dict()
    target_margins = dict()
    margins_by_variable = dict()
    parameters = {
        'use_proportions': True,
        'initial_weight': None,
        'method': None,  # 'linear', 'raking ratio', 'logit'
        'up': None,
        'lo': None
        }
    period = None
    simulation = None
    target_entity_count = None
    weight_name = None

    def __init__(self, simulation, target_margins, period, target_entity_count = None, parameters = None,
            filter_by = None, entity = None):
        self.period = period
        self.simulation = simulation
        if target_margins:
            margin_variables = list(target_margins.keys())
        else:
            margin_variables = []

        variable_instance_by_variable_name = simulation.tax_benefit_system.variables
        entities = set(
            variable_instance_by_variable_name[variable].entity.key
            for variable in margin_variables
            )

        if len(entities) == 0:
            assert target_entity_count != 0
            assert entity in [
                entity.key
                for entity in simulation.tax_benefit_system.entities
                ]
        elif len(entities) > 1:
            raise NotImplementedError("Cannot hande multiple entites")
        else:
            entity = list(entities)[0]

        assert simulation.weight_variable_by_entity is not None

        weight_variable_name = simulation.weight_variable_by_entity.get(entity)
        self.weight_name = weight_name = weight_variable_name

        self.entity = entity
        period = self.period

        if filter_by:
            self.filter_by = simulation.calculate(filter_by, period = period)
        else:
            self.filter_by = numpy.array(1.0)

        assert weight_name is not None, "A calibration needs a weight variable name to act on"
        self._initial_weight_name = weight_name + "_ini"
        self.initial_weight = initial_weight = simulation.calculate(weight_name, period = period)

        self.initial_entity_count = sum(initial_weight * self.filter_by)
        self.target_entity_count = target_entity_count

        self.weight = initial_weight.copy()

        # TODO does not work
        for entity, weight_variable in simulation.weight_variable_by_entity.items():
            self.initial_weight_by_entity[entity] = simulation.calculate(weight_variable, period = period)

        if target_margins:
            for variable, target in target_margins.items():
                self.set_target_margin(variable, target)

        self.parameters = parameters

    def _build_calmar_data(self) -> pd.DataFrame:
        """Build the data dictionnary used as calmar input argument.

        Returns:
            pd.DataFrame: Data used by calmar
        """
        # Select only filtered entities
        assert self._initial_weight_name is not None
        data = pd.DataFrame()
        data[self._initial_weight_name] = self.initial_weight * self.filter_by
        period = self.period
        for variable in self.margins_by_variable:
            assert variable in self.simulation.tax_benefit_system.variables
            data[variable] = self.simulation.calculate(variable, period = period)

        return data

    def calibrate(self, inplace = False):
        """Apply the calibrations by updating weights and margins.

        Args:
            inplace (bool, optional): Whether to return the calibrated or to setthem inplace. Defaults to False.

        Returns:
            numpy.array: calibrated weights
        """
        assert self.margins_by_variable is not None, "Margins by variable should be set"
        margins_by_variable = self.margins_by_variable
        parameters = self.get_parameters()

        if margins_by_variable is not None:
            simple_margins_by_variable = dict([
                (variable, margins_by_type['target'])
                for variable, margins_by_type in margins_by_variable.items()])
        else:
            simple_margins_by_variable = dict()

        if self.target_entity_count:
            simple_margins_by_variable['total_population'] = self.target_entity_count

        self._update_weights(simple_margins_by_variable, parameters = parameters)
        self._update_margins()
        if inplace:
            self.set_calibrated_weights()
            return

        return self.weight

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

    def set_target_margin(self, variable, target):
        """Set variable target margin.

        Args:
          variable: Target variable
          target: Target value
        """
        simulation = self.simulation
        period = self.period
        assert variable in simulation.tax_benefit_system.variables
        variable_instance = simulation.tax_benefit_system.variables[variable]

        filter_by = self.filter_by
        target_by_category = None
        categorical_variable = (
            (variable_instance.value_type in [bool, Enum])
            or (variable_instance.unit == 'years')
            or (variable_instance.unit == 'months')
            )
        if categorical_variable:
            value = simulation.calculate(variable, period = period)
            filtered_value = value if all(filter_by) else value[filter_by.astype(bool)]
            categories = numpy.sort(numpy.unique(filtered_value))
            target_by_category = dict(zip(categories, target))

        if not self.margins_by_variable:
            self.margins_by_variable = dict()
        if variable not in self.margins_by_variable:
            self.margins_by_variable[variable] = dict()
        self.margins_by_variable[variable]['target'] = target_by_category or target
        self._update_margins()

    def reset(self):
        """Reset the calibration to its initial state."""
        simulation = self.simulation
        simulation.delete_arrays(self.weight_name, self.period)
        simulation.set_input(self.weight_name, self.period, numpy.array(self.initial_weight))

    def set_calibrated_weights(self):
        """Modify the weights to use the calibrated weights."""
        period = self.period
        simulation = self.simulation
        simulation.set_input(self.weight_name, period, self.weight)
        for weight_name in simulation.weight_variable_by_entity.values():
            if weight_name == self.weight_name:
                continue
            # Delete other entites already computed weigths
            # to ensure that this weights a recomputed if they derive from
            # the calibrated weight variable
            weight_variable = simulation.tax_benefit_system.variables[weight_name]
            if weight_variable.formulas:
                simulation.delete_arrays(weight_variable.name, period)

    def summary(self):
        """Summarize margins."""
        margins_df = pd.DataFrame.from_dict(self.margins_by_variable).T
        margins_df.loc['entity_count', 'actual'] = (self.weight * self.filter_by).sum()
        margins_df.loc['entity_count', 'initial'] = (self.initial_weight * self.filter_by).sum()
        margins_df.loc['entity_count', 'target'] = self.target_entity_count
        return margins_df

    def _update_margins(self):
        """Update margins."""
        for variable in self.margins_by_variable:
            simulation = self.simulation
            period = self.period
            entity = self.entity

            # These are the varying weights
            weight = self.weight
            filter_by = self.filter_by
            initial_weight = self.initial_weight

            value = simulation.calculate(variable, period = period)
            weight_variable = simulation.weight_variable_by_entity[entity]

            # weight = simulation.calculate(weight_variable, period)
            # initial_weight = self.initial_weight_by_entity[entity]

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

            variable_instance = simulation.tax_benefit_system.get_variable(variable)
            assert variable_instance is not None
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

        entity = self.entity
        weight_variable = self.simulation.weight_variable_by_entity[entity]

        if self.weight_name != weight_variable:
            raise NotImplementedError("Calmar needs to be adapted. Consider using a projected target on the entity with changing weights")

        data = self._build_calmar_data()

        assert self._initial_weight_name is not None
        parameters['initial_weight'] = self._initial_weight_name
        if self.target_entity_count:
            margins["total_population"] = self.target_entity_count

        val_pondfin, lambdasol, updated_margins = calmar(
            data, margins, **parameters)
        # Updating only afetr filtering weights
        self.weight = val_pondfin * self.filter_by + self.weight * (logical_not(self.filter_by))

        return updated_margins
