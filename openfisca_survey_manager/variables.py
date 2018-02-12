# -*- coding: utf-8 -*-

from numpy import arange

from openfisca_core.variables import Variable
from openfisca_core.model_api import Enum
from openfisca_survey_manager.statshelpers import weighted_quantiles


class Quantile(Variable):
    def __init__(self, name, attributes, variable_class):
        self.name = name
        self.attributes = attributes
        assert 'q' in self.attributes
        assert 'variable' in self.attributes
        self.attributes['value_type'] = Enum
        q = self.attributes['q']

        if 'possible_values' in self.attributes:
            possible_values = self.attributes['possible_values']
            assert len(possible_values) == q
        variable = self.attributes['variable']
        weight_variable = self.attributes['weight_variable']
        # filter_variable = self.attributes['filter_variable']

        def forumla(entity, period):
            value = entity(variable, period)
            weight = entity(weight_variable, period)
            # filter = entity(filter_variable, period)
            labels = arange(1, q + 1)
            quantile, _ = weighted_quantiles(
                value,
                labels,
                weight,  # * filter,
                return_quantiles = True,
                )
            return quantile

        self.variable_class = variable_class
        Variable.__init__(self, self.name, self.attributes, self.variable_class)
