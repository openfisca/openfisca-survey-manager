"""Abstract survey scenario definition."""

import logging
import numpy as np
import pandas as pd


from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario


log = logging.getLogger(__name__)


class ReformScenario(AbstractSurveyScenario):
    """Reform survey scenario."""

    baseline_simulation = None
    baseline_tax_benefit_system = None

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
        if use_baseline:
            assert self.baseline_simulation is not None, "self.baseline_simulation is None"
            simulation = self.baseline_simulation
        else:
            assert self.simulation is not None
            simulation = self.simulation

        return simulation.adaptative_calculate_variable(variable, period = period)

    def compute_aggregate(self, variable = None, aggfunc = 'sum', filter_by = None, period = None, use_baseline = False,
            difference = False, missing_variable_default_value = np.nan, weighted = True, alternative_weights = None):
        """Compute variable aggregate.

        Args:
          variable: Variable (Default value = None)
          aggfunc: Aggregation function (Default value = 'sum')
          filter_by: Filtering variable (Default value = None)
          period: Period in which the variable is computed. If None, simulation.period is chosen (Default value = None)
          use_baseline: Use baseline simulation (Default value = False)
          difference:  Compute difference between simulation and baseline (Default value = False)
          missing_variable_default_value: Value of missing variable (Default value = np.nan)
          weighted: Whether to weight te aggregates (Default value = True)
          alternative_weights: Weight variable name or numerical value. Use SurveyScenario's weight_variable_by_entity if None, and if the latetr is None uses 1 ((Default value = None)

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
        if use_baseline:
            simulation = self.baseline_simulation
            assert simulation is not None, "Missing baseline simulation"
        else:
            simulation = self.simulation
            assert simulation is not None, "Missing (reform) simulation"

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

    def compute_quantiles(self, variable = None, nquantiles = None, period = None, use_baseline = False, filter_by = None,
            weighted = True, alternative_weights = None):

        assert variable is not None
        assert nquantiles is not None
        if use_baseline:
            simulation = self.baseline_simulation
            assert simulation is not None, "Missing baseline simulation"
        else:
            simulation = self.simulation
            assert simulation is not None, "Missing (reform) simulation"

        return simulation.compute_quantiles(
            variable = variable,
            period = period,
            nquantiles = nquantiles,
            filter_by = filter_by,
            weighted = weighted,
            alternative_weights = alternative_weights,
            )

    def compute_marginal_tax_rate(self, target_variable, period, use_baseline = False,
            value_for_zero_varying_variable = 0.0):
        """
        Compute marginal a rate of a target (MTR) with respect to a varying variable.

        Args:
            target_variable (str): the variable which marginal tax rate is computed
            period (Period): the period at which the the marginal tax rate is computed
            use_baseline (bool, optional): compute the marginal tax rate for the baseline system. Defaults to False.
            value_for_zero_varying_variable (float, optional): value of MTR when the varying variable is zero. Defaults to 0.

        Returns:
            numpy.array: Vector of marginal rates
        """
        varying_variable = self.varying_variable
        if use_baseline:
            simulation = self.baseline_simulation
            assert self._modified_baseline_simulation is not None
            modified_simulation = self._modified_baseline_simulation
        else:
            assert self._modified_simulation is not None
            simulation = self.simulation
            modified_simulation = self._modified_simulation

        assert target_variable in self.tax_benefit_system.variables

        variables_belong_to_same_entity = (
            self.tax_benefit_system.variables[varying_variable].entity.key
            == self.tax_benefit_system.variables[target_variable].entity.key
            )
        varying_variable_belongs_to_person_entity = self.tax_benefit_system.variables[varying_variable].entity.is_person

        assert variables_belong_to_same_entity or varying_variable_belongs_to_person_entity

        if variables_belong_to_same_entity:
            modified_varying = modified_simulation.calculate_add(varying_variable, period = period)
            varying = simulation.calculate_add(varying_variable, period = period)
        else:
            target_variable_entity_key = self.tax_benefit_system.variables[target_variable].entity.key

            def cast_to_target_entity(simulation):
                population = simulation.populations[target_variable_entity_key]
                df = (pd.DataFrame(
                    {
                        'members_entity_id': population._members_entity_id,
                        varying_variable: simulation.calculate_add(varying_variable, period = period)
                        }
                    ).groupby('members_entity_id').sum())
                varying_variable_for_target_entity = df.loc[population.ids, varying_variable].values
                return varying_variable_for_target_entity

            modified_varying = cast_to_target_entity(modified_simulation)
            varying = cast_to_target_entity(simulation)

        modified_target = modified_simulation.calculate_add(target_variable, period = period)
        target = simulation.calculate_add(target_variable, period = period)

        numerator = modified_target - target
        denominator = modified_varying - varying
        marginal_rate = 1 - np.divide(
            numerator,
            denominator,
            out = np.full_like(numerator, value_for_zero_varying_variable, dtype = np.floating),
            where = (denominator != 0)
            )

        return marginal_rate

    def compute_pivot_table(self, aggfunc = 'mean', columns = None, difference = False, filter_by = None, index = None,
            period = None, use_baseline = False, use_baseline_for_columns = None, values = None,
            missing_variable_default_value = np.nan, concat_axis = None, weighted = True, alternative_weights = None):
        """Compute a pivot table of agregated values casted along specified index and columns.

        Args:
            aggfunc(str, optional): Aggregation function, defaults to 'mean'
            columns(list, optional): Variable(s) in columns, defaults to None
            difference(bool, optional): Compute difference, defaults to False
            filter_by(str, optional): Boolean variable to filter by, defaults to None
            index(list, optional): Variable(s) in index (lines), defaults to None
            period(Period, optional): Period, defaults to None
            use_baseline(bool, optional): Compute for baseline, defaults to False
            use_baseline_for_columns(bool, optional): Use columns from baseline columns values, defaults to None
            values(list, optional): Aggregated variable(s) within cells, defaults to None
            missing_variable_default_value(float, optional): Default value for missing variables, defaults to np.nan
            concat_axis(int, optional): Axis to concatenate along (index = 0, columns = 1), defaults to None
            weighted(bool, optional): Whether to weight te aggregates (Default value = True)
            alternative_weights(str or int or float, optional): Weight variable name or numerical value. Use Simulation's weight_variable_by_entity if None, and if the later is None uses 1 ((Default value = None)

        Returns:
            pd.DataFrame: Pivot table

        """
        assert aggfunc in ['count', 'mean', 'sum']
        assert columns or index or values
        assert not (difference and use_baseline), "Can't have difference and use_baseline both set to True"

        simulation = self.simulation
        baseline_simulation = None
        if difference:
            baseline_simulation = self.baseline_simulation

        if use_baseline:
            simulation = baseline_simulation = self.baseline_simulation

        filtering_variable_by_entity = self.filtering_variable_by_entity

        return simulation.compute_pivot_table(
            baseline_simulation = baseline_simulation,
            aggfunc = aggfunc,
            columns = columns,
            difference = difference,
            filter_by = filter_by,
            index = index,
            period = period,
            use_baseline_for_columns = use_baseline_for_columns,
            values = values,
            missing_variable_default_value = missing_variable_default_value,
            concat_axis = concat_axis,
            weighted = weighted,
            alternative_weights = alternative_weights,
            filtering_variable_by_entity = filtering_variable_by_entity,
            )

    def compute_winners_loosers(self, variable = None,
            filter_by = None,
            period = None,
            absolute_minimal_detected_variation = 0,
            relative_minimal_detected_variation = .01,
            observations_threshold = None,
            weighted = True,
            alternative_weights = None):

        simulation = self.simulation
        baseline_simulation = self.baseline_simulation

        return simulation.compute_winners_loosers(
            baseline_simulation,
            variable = variable,
            filter_by = filter_by,
            period = period,
            absolute_minimal_detected_variation = absolute_minimal_detected_variation,
            relative_minimal_detected_variation = relative_minimal_detected_variation,
            observations_threshold = observations_threshold,
            weighted = weighted,
            alternative_weights = alternative_weights,
            filtering_variable_by_entity = self.filtering_variable_by_entity,
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
        simulation = self.baseline_simulation if (use_baseline and self.baseline_simulation) else self.simulation
        # tax_benefit_system = self.baseline_tax_benefit_system if (
        #     use_baseline and self.baseline_tax_benefit_system
        #     ) else self.tax_benefit_system

        id_variable_by_entity_key = self.id_variable_by_entity_key

        return simulation.create_data_frame_by_entity(
            variables = variables,
            expressions = expressions,
            filter_by = filter_by,
            index = index,
            period = period,
            merge = merge,
            id_variable_by_entity_key = id_variable_by_entity_key,
            )
