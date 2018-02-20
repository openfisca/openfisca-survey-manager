# -*- coding: utf-8 -*-

from numpy import arange

from openfisca_core.formulas import Formula
from openfisca_core.variables import Variable, VALUE_TYPES, Enum, MONTH, YEAR, ETERNITY
from openfisca_core.model_api import where
from openfisca_survey_manager.statshelpers import mark_weighted_percentiles


class Quantile(Variable):
    def __init__(self, baseline_variable = None):
        self.name = unicode(self.__class__.__name__)
        attr = dict(self.__class__.__dict__)

        assert 'q' in attr
        assert 'variable' in attr
        variable = attr.pop('variable')
        q = attr.pop('q')
        filter_variable = None
        weight_variable = None
        if 'weight_variable' in attr:
            weight_variable = attr.pop('weight_variable')

        if 'filter_variable' in attr:
            filter_variable = attr.pop('filter_variable')

        attr['value_type'] = int
        self.baseline_variable = baseline_variable
        self.value_type = self.set(attr, 'value_type', required = True, allowed_values = VALUE_TYPES.keys())
        self.dtype = VALUE_TYPES[self.value_type]['dtype']
        self.json_type = VALUE_TYPES[self.value_type]['json_type']
        if self.value_type == Enum:
            self.possible_values = self.set(attr, 'possible_values', required = True, allowed_type = Enum)
        if self.value_type == str:
            self.max_length = self.set(attr, 'max_length', allowed_type = int)
            if self.max_length:
                self.dtype = '|S{}'.format(self.max_length)
        default_type = int if self.value_type == Enum else self.value_type
        self.default_value = self.set(attr, 'default_value', allowed_type = default_type,
            default = VALUE_TYPES[self.value_type]['default'])
        self.entity = self.set(attr, 'entity', required = True, setter = self.set_entity)
        self.definition_period = self.set(attr, 'definition_period', required = True,
            allowed_values = (MONTH, YEAR, ETERNITY))
        self.label = self.set(attr, 'label', allowed_type = basestring, setter = self.set_label)
        self.end = self.set(attr, 'end', allowed_type = basestring, setter = self.set_end)
        self.reference = self.set(attr, 'reference', setter = self.set_reference)
        self.cerfa_field = self.set(attr, 'cerfa_field', allowed_type = (basestring, dict))
        self.unit = self.set(attr, 'unit', allowed_type = basestring)
        self.set_input = self.set_set_input(attr.pop('set_input', None))
        self.calculate_output = self.set_calculate_output(attr.pop('calculate_output', None))
        self.is_period_size_independent = self.set(attr, 'is_period_size_independent', allowed_type = bool,
            default = VALUE_TYPES[self.value_type]['is_period_size_independent'])
        self.base_function = self.set_base_function(attr.pop('base_function', None))

        # if 'possible_values' in self.attributes:
        #     possible_values = self.attributes['possible_values']
        #     assert len(possible_values) == q

        def formula(entity, period):
            value = entity(variable, period)
            if weight_variable is not None:
                weight = entity(weight_variable, period)
            weight = entity.filled_array(1)
            if filter_variable is not None:
                filter_value = entity(filter_variable, period)
                weight = filter_value * weight

            labels = arange(1, q + 1)
            quantile, _ = mark_weighted_percentiles(
                value,
                labels,
                weight,
                method = 2,  # * filter,
                return_quantiles = True,
                )
            if filter_variable is not None:
                quantile = where(weight > 0, quantile, -1)
            return quantile

        attr['formula'] = formula
        self.formula = Formula.build_formula_class(attr, self, baseline_variable = baseline_variable)
        self.is_neutralized = False
