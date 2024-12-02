"""Abstract survey scenario definition."""

import logging
import numpy as np
import pandas as pd

from typing import Optional, Union
from openfisca_core.types import Array, Period

from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario
from openfisca_survey_manager.simulations import Simulation


log = logging.getLogger(__name__)


class ReformScenario(AbstractSurveyScenario):
    """Reform survey scenario."""

    def _get_simulation(self, use_baseline: bool = False):
        """
        Get relevant simulation

        Args:
            use_baseline (bool, optional): Whether to get baseline or reform simulation. Defaults to False.
        """

        if len(self.simulations) == 1:
            return list(self.simulations.values())[0]

        simulation_name = (
            "baseline"
            if use_baseline
            else "reform"
            )
        simulation = self.simulations[simulation_name]
        assert simulation is not None, f"{simulation_name} does not exist"
        return simulation

    def build_input_data(self, **kwargs):
        """Build input data."""
        NotImplementedError

    def calculate_series(self, variable, period = None, use_baseline = False):
        """Compute variable values for period and baseline or reform tax benefit and system.

        Args:
          variable(str, optional): Variable to compute
          period(Period, optional): Period, defaults to None
          use_baseline(bool, optional): Use baseline tax and benefit system, defaults to False

        Returns:
          pandas.Series: Variable values

        """
        return pd.Series(
            data = self.calculate_variable(variable, period, use_baseline),
            name = variable,
            )

    def calculate_variable(self, variable, period = None, use_baseline = False):
        """Compute variable values for period and baseline or reform tax benefit and system.

        Args:
          variable(str, optional): Variable to compute
          period(Period, optional): Period, defaults to None
          use_baseline(bool, optional): Use baseline tax and benefit system, defaults to False

        Returns:
          numpy.ndarray: Variable values

        """
        simulation = self._get_simulation(use_baseline)
        return simulation.adaptative_calculate_variable(variable, period = period)

    def compute_aggregate(self, variable: str = None, aggfunc: str = 'sum', filter_by: str = None,
            period: Optional[Union[int, str, Period]] = None, use_baseline: bool = False,
            difference: bool = False, missing_variable_default_value = np.nan, weighted: bool = True,
            alternative_weights: Optional[Union[str, int, float, Array]] = None):
        """Compute variable aggregate.

        Args:
            variable (str, optional): Variable to aggregate. Defaults to None.
            aggfunc (str, optional): Aggregation function. Defaults to 'sum'.
            filter_by (str, optional): Filter variable or expression to use. Defaults to None.
            period (Optional[Union[int, str, Period]], optional): Period. Defaults to None.
            use_baseline: Use baseline simulation. Defaults to False.
            missing_variable_default_value (optional): Value to use for missing values. Defaults to np.nan.
            weighted (bool, optional): Whether to weight the variable or not. Defaults to True.
            alternative_weights (Optional[Union[str, int, float, Array]], optional): Alternative weigh to use. Defaults to None.
            filtering_variable_by_entity (Dict, optional): Filtering variable by entity. Defaults to None.

        Returns:
            float: Aggregate
        """
        assert aggfunc in ['count', 'mean', 'sum', 'count_non_zero']
        assert period is not None
        assert not (difference and use_baseline), "Can't have difference and use_baseline both set to True"

        if difference:
            return (
                self.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    use_baseline = False,
                    missing_variable_default_value = missing_variable_default_value,
                    weighted = weighted,
                    alternative_weights = alternative_weights,
                    )
                - self.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    use_baseline = True,
                    missing_variable_default_value = missing_variable_default_value,
                    weighted = weighted,
                    alternative_weights = alternative_weights,
                    )
                )

        assert variable is not None
        simulation = self._get_simulation(use_baseline)
        return simulation.compute_aggregate(
            variable = variable,
            aggfunc = aggfunc,
            filter_by = filter_by,
            period = period,
            missing_variable_default_value = missing_variable_default_value,
            weighted = weighted,
            alternative_weights = alternative_weights,
            filtering_variable_by_entity = self.filtering_variable_by_entity,
            )

    def compute_quantiles(self, variable: str = None, nquantiles = None, period = None, use_baseline = False, filter_by = None,
            weighted = True, alternative_weights = None):

        assert variable is not None
        assert nquantiles is not None
        simulation = self._get_simulation(use_baseline)

        return simulation.compute_quantiles(
            variable = variable,
            period = period,
            nquantiles = nquantiles,
            filter_by = filter_by,
            weighted = weighted,
            alternative_weights = alternative_weights,
            )

    def compute_marginal_tax_rate(self, target_variable: str, period: Optional[Union[int, str, Period]], use_baseline: bool = False,
            value_for_zero_varying_variable: float = 0.0) -> Array:
        """
        Compute marginal a rate of a target (MTR) with respect to a varying variable.

        Args:
            target_variable (str): the variable which marginal tax rate is computed
            period (Optional[Union[int, str, Period]], optional): Period. Defaults to None.
            use_baseline: Use baseline simulation. Defaults to False.
            value_for_zero_varying_variable (float, optional): value of MTR when the varying variable is zero. Defaults to 0.

        Returns:
            numpy.array: Vector of marginal rates
        """
        if use_baseline:
            return super(ReformScenario, self).compute_marginal_tax_rate(
                target_variable = target_variable,
                period = period,
                simulation = "baseline",
                value_for_zero_varying_variable = value_for_zero_varying_variable,
                )
        else:
            return super(ReformScenario, self).compute_marginal_tax_rate(
                target_variable = target_variable,
                period = period,
                simulation = "reform",
                value_for_zero_varying_variable = value_for_zero_varying_variable,
                )

    def compute_pivot_table(self, aggfunc = 'mean', columns = None, difference = False, filter_by = None, index = None,
            period = None, use_baseline = False, use_baseline_for_columns = None, values = None,
            missing_variable_default_value = np.nan, concat_axis = None, weighted = True, alternative_weights = None):

        filtering_variable_by_entity = self.filtering_variable_by_entity

        return Simulation.compute_pivot_table(
            aggfunc = aggfunc,
            columns = columns,
            baseline_simulation = self._get_simulation(use_baseline = True),
            filter_by = filter_by,
            index = index,
            period = period,
            simulation = self._get_simulation(use_baseline),
            difference = difference,
            use_baseline_for_columns = use_baseline_for_columns,
            values = values,
            missing_variable_default_value = missing_variable_default_value,
            concat_axis = concat_axis,
            weighted = weighted,
            alternative_weights = alternative_weights,
            filtering_variable_by_entity = filtering_variable_by_entity
            )

    def compute_winners_loosers(self, variable = None,
            filter_by = None,
            period = None,
            absolute_minimal_detected_variation = 0,
            relative_minimal_detected_variation = .01,
            observations_threshold = None,
            weighted = True,
            alternative_weights = None):

        return super(ReformScenario, self).compute_winners_loosers(
            simulation = "reform",
            baseline_simulation = "baseline",
            variable = variable,
            filter_by = filter_by,
            period = period,
            absolute_minimal_detected_variation = absolute_minimal_detected_variation,
            relative_minimal_detected_variation = relative_minimal_detected_variation,
            observations_threshold = observations_threshold,
            weighted = weighted,
            alternative_weights = alternative_weights,
            )

    def create_data_frame_by_entity(self, variables = None, expressions = None, filter_by = None, index = False,
            period = None, use_baseline = False, merge = False):
        """Create dataframe(s) of computed variable for every entity (eventually merged in a unique dataframe).

        Args:
          variables(list, optional): Variable to compute, defaults to None
          expressions(str, optional): Expressions to compute, defaults to None
          filter_by(str, optional): Boolean variable or expression, defaults to None
          index(bool, optional): Index by entity id, defaults to False
          period(Period, optional): Period, defaults to None
          use_baseline(bool, optional): Use baseline tax and benefit system, defaults to False
          merge(bool, optional): Merge all the entities in one data frame, defaults to False

        Returns:
          dict or pandas.DataFrame: Dictionnary of dataframes by entities or dataframe with all the computed variables

        """
        simulation = self._get_simulation(use_baseline)
        return simulation.create_data_frame_by_entity(
            variables = variables,
            expressions = expressions,
            filter_by = filter_by,
            index = index,
            period = period,
            merge = merge,
            )
