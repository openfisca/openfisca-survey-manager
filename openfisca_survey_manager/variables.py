import logging
from numpy import arange

from openfisca_core.model_api import Variable, ADD, where, YEAR
from openfisca_survey_manager.statshelpers import (
    mark_weighted_percentiles,
    weightedcalcs_quantiles
    )

log = logging.getLogger(__name__)


def create_quantile(x, nquantiles, weight_variable, entity_name):
    class quantile(Variable):
        value_type = int
        entity = entity_name
        label = "Quantile"
        definition_period = YEAR

        def formula(entity, period):
            try:
                variable = entity(x, period)
            except ValueError as e:
                log.debug(f"Caught {e}")
                log.debug(f"Computing on whole period {period} via the ADD option")
                variable = entity(x, period, options = [ADD])

            weight = entity(weight_variable, period)
            labels = arange(1, nquantiles + 1)
            method = 2
            if len(weight) == 1:
                return weight * 0
            quantile, values = mark_weighted_percentiles(variable, labels, weight, method, return_quantiles = True)
            del values
            return quantile

    return quantile


def quantile(q, variable, weight_variable = None, filter_variable = None):
    """
    Return quantile of a variable with weight provided by a specific wieght variable potentially filtered
    """
    def formula(entity, period):
        value = entity(variable, period)
        if weight_variable is not None:
            weight = entity(weight_variable, period)
        weight = entity.filled_array(1)
        if filter_variable is not None:
            filter_value = entity(filter_variable, period)
            weight = filter_value * weight

        labels = arange(1, q + 1)
        quantile, _ = weightedcalcs_quantiles(
            value,
            labels,
            weight,
            return_quantiles = True,
            )
        if filter_variable is not None:
            quantile = where(weight > 0, quantile, -1)
        return quantile

    return formula


def old_quantile(q, variable, weight_variable = None, filter_variable = None):
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
