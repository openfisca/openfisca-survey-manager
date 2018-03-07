# -*- coding: utf-8 -*-

from numpy import arange

from openfisca_core.formulas import Formula
from openfisca_core.variables import Variable, VALUE_TYPES, Enum, MONTH, YEAR, ETERNITY
from openfisca_core.model_api import where
from openfisca_survey_manager.statshelpers import mark_weighted_percentiles


def quantile(q, variable, weight_variable = None, filter_variable = None):
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

    return formula
