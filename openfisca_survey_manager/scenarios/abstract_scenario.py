"""Abstract survey scenario definition."""

import logging
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union


from openfisca_core import periods
from openfisca_core.types import Array, Period, TaxBenefitSystem
from openfisca_survey_manager.simulations import Simulation  # noqa analysis:ignore
from openfisca_core.periods import MONTH, YEAR
from openfisca_core.tools.simulation_dumper import dump_simulation, restore_simulation


from openfisca_survey_manager.calibration import Calibration
from openfisca_survey_manager.surveys import Survey

log = logging.getLogger(__name__)


class AbstractSurveyScenario(object):
    """Abstract survey scenario."""

    cache_blacklist = None
    collection = None
    debug = False
    filtering_variable_by_entity = None
    id_variable_by_entity_key = None
    inflator_by_variable = None  # factor used to inflate variable total
    input_data_frame = None
    input_data_table_by_entity_by_period = None
    input_data_table_by_period = None
    non_neutralizable_variables = None
    period = None
    role_variable_by_entity_key = None
    simulations = None
    target_by_variable = None  # variable total target to inflate to
    tax_benefit_systems = None
    trace = False
    used_as_input_variables = None
    used_as_input_variables_by_entity = None
    variation_factor = .03  # factor used to compute variation when estimating marginal tax rate
    varying_variable = None
    weight_variable_by_entity = None

    def build_input_data(self, **kwargs):
        """Build input data."""
        NotImplementedError

    def calculate_series(self, variable, period = None, simulation = None):
        """Compute variable values for period for a given simulation.

        Args:
          variable(str, optional): Variable to compute
          period(Period, optional): Period, defaults to None
          simulation(str, optional): Simulation to use

        Returns:
          pandas.Series: Variable values

        """
        return pd.Series(
            data = self.calculate_variable(variable, period, simulation = simulation),
            name = variable,
            )

    def calculate_variable(self, variable, period = None, simulation = None):
        """Compute variable values for period for a given simulation.

        Args:
          variable(str, optional): Variable to compute
          period(Period, optional): Period, defaults to None
          simulation(str, optional): Simulation to use

        Returns:
          numpy.ndarray: Variable values

        """
        if simulation is None:
            assert len(self.simulations.keys()) == 1
            simulation = list(self.simulations.values())[0]
        else:
            simulation = self.simulations[simulation]
        assert simulation is not None
        return simulation.adaptative_calculate_variable(variable, period = period)

    def calibrate(self, period: int = None, target_margins_by_variable: dict = None, parameters: dict = None,
            target_entity_count: float = None, other_entity_count: float = None, entity: str = None):
        """Calibrate the scenario data.

        Args:
            period (int, optionnal): Period of calibration. Defaults to scenario.year
            target_margins_by_variable (dict, optional): Variable targets margins. Defaults to None.
            parameters (dict, optional): Calibration parameters. Defaults to None.
            target_entity_count (float, optional): Total population target. Defaults to None.
            other_entity_count (float, optional): Total population target of the second entity. Defaults to None.
            entity (str): Entity specified when no variable comes with a target margins but `target_entity_count` is not None.
        """
        survey_scenario = self

        if period is None:
            assert survey_scenario.period is not None
            period = survey_scenario.period

        if parameters is not None:
            assert parameters['method'] in ['linear', 'raking ratio', 'logit', 'hyperbolic sinus'], \
                "Incorect parameter value: method should be 'linear', 'raking ratio', 'logit' or 'hyperbolic sinus'"
            if parameters['method'] == 'logit':
                assert parameters['invlo'] is not None
                assert parameters['up'] is not None
            elif parameters['method'] == 'hyperbolic sinus':
                assert parameters['alpha'] is not None
        else:
            parameters = dict(method = 'logit', up = 3, invlo = 3)

        # TODO: filtering using filtering_variable_by_entity
        for simulation in self.simulations.values():
            if simulation is None:
                continue
            calibration = Calibration(
                simulation,
                target_margins_by_variable,
                period,
                target_entity_count = target_entity_count,
                other_entity_count = other_entity_count,
                entity = entity,
                parameters = parameters,
                # filter_by = self.filter_by,
                )
            calibration.calibrate(inplace = True)
            simulation.calibration = calibration

    def compute_aggregate(self, variable: str = None, aggfunc: str = 'sum', filter_by: str = None,
            period: Optional[Union[int, str, Period]] = None,
            simulation: str = None, baseline_simulation: str = None, missing_variable_default_value = np.nan,
            weighted: bool = True, alternative_weights: Optional[Union[str, int, float, Array]] = None):
        """Compute variable aggregate.

        Args:
            variable (str, optional): Variable to aggregate. Defaults to None.
            aggfunc (str, optional): Aggregation function. Defaults to 'sum'.
            filter_by (str, optional): Filter variable or expression to use. Defaults to None.
            period (Optional[Union[int, str, Period]], optional): Period. Defaults to None.
            simulation(str, optional): Simulation to use
            baseline_simulation(str, optional): Baseline simulation to use when computing a difference
            missing_variable_default_value (optional): Value to use for missing values. Defaults to np.nan.
            weighted (bool, optional): Whether to weight the variable or not. Defaults to True.
            alternative_weights (Optional[Union[str, int, float, Array]], optional): Alternative weigh to use. Defaults to None.
            filtering_variable_by_entity (Dict, optional): Filtering variable by entity. Defaults to None.

        Returns:
            float: Aggregate
        """
        assert aggfunc in ['count', 'mean', 'sum', 'count_non_zero']
        assert period is not None
        assert variable is not None
        if simulation is None:
            assert len(self.simulations.keys()) == 1
            simulation = list(self.simulations.values())[0]
        else:
            simulation = self.simulations[simulation]

        assert simulation is not None, f"Missing {simulation} simulation"

        if baseline_simulation:
            baseline_simulation = self.simulations[baseline_simulation]
            return (
                simulation.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    missing_variable_default_value = missing_variable_default_value,
                    weighted = weighted,
                    alternative_weights = alternative_weights,
                    filtering_variable_by_entity = self.filtering_variable_by_entity,
                    )
                - baseline_simulation.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    missing_variable_default_value = missing_variable_default_value,
                    weighted = weighted,
                    alternative_weights = alternative_weights,
                    filtering_variable_by_entity = self.filtering_variable_by_entity,
                    )
                )

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

    def compute_quantiles(self, simulation: Simulation, variable: str, nquantiles: int = None,
            period: Optional[Union[int, str, Period]] = None, filter_by = None, weighted: bool = True,
            alternative_weights = None, filtering_variable_by_entity = None) -> List[float]:
        """
        Compute quantiles of a variable.

        Args:
            simulation (Simulation, optional): Simulation to be used. Defaults to None.
            variable (str, optional): Variable which quantiles are computed. Defaults to None.
            nquantiles (int, optional): Number of quantiles. Defaults to None.
            period (Optional[Union[int, str, Period]], optional): Period. Defaults to None.
            missing_variable_default_value (optional): Value to use for missing values. Defaults to np.nan.
            weighted (bool, optional): Whether to weight the variable or not. Defaults to True.
            alternative_weights (Optional[Union[str, int, float, Array]], optional): Alternative weigh to use. Defaults to None.
            filtering_variable_by_entity (Dict, optional): Filtering variable by entity. Defaults to None.

        Returns:
        List(float): The quantiles values
        """
        assert variable is not None
        assert nquantiles is not None
        simulation = self.simulations[simulation]
        assert simulation is not None, f"Missing {simulation} simulation"

        return simulation.compute_quantiles(
            variable = variable,
            period = period,
            nquantiles = nquantiles,
            filter_by = filter_by,
            weighted = weighted,
            alternative_weights = alternative_weights,
            )

    def compute_marginal_tax_rate(self, target_variable: str, period: Optional[Union[int, str, Period]], simulation: str = None,
            value_for_zero_varying_variable: float = 0.0) -> Array:
        """
        Compute marginal a rate of a target (MTR) with respect to a varying variable.

        Args:
            target_variable (str): the variable which marginal tax rate is computed
            period (Optional[Union[int, str, Period]], optional): Period. Defaults to None.
            simulation(str, optional): Simulation to use
            value_for_zero_varying_variable (float, optional): value of MTR when the varying variable is zero. Defaults to 0.

        Returns:
            numpy.array: Vector of marginal rates
        """
        varying_variable = self.varying_variable
        if simulation is None:
            assert len(self.simulations.keys()) == 2
            simulation_name = [name for name in self.simulations.keys() if not name.startswith("_modified_")][0]
            simulation = self.simulations[simulation_name]
        else:
            simulation_name = simulation
            simulation = self.simulations[simulation_name]

        modified_simulation = self.simulations[f"_modified_{simulation_name}"]

        variables = simulation.tax_benefit_system.variables
        assert target_variable in variables

        variables_belong_to_same_entity = (
            variables[varying_variable].entity.key == variables[target_variable].entity.key
            )
        varying_variable_belongs_to_person_entity = variables[varying_variable].entity.is_person

        assert variables_belong_to_same_entity or varying_variable_belongs_to_person_entity

        if variables_belong_to_same_entity:
            modified_varying = modified_simulation.calculate_add(varying_variable, period = period)
            varying = simulation.calculate_add(varying_variable, period = period)
        else:
            target_variable_entity_key = variables[target_variable].entity.key

            def cast_to_target_entity(simulation: Simulation):
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

    def compute_pivot_table(self, aggfunc = 'mean', columns = None, baseline_simulation = None, filter_by = None, index = None,
            period = None, simulation = None, difference = False, use_baseline_for_columns = None, values = None,
            missing_variable_default_value = np.nan, concat_axis = None, weighted = True, alternative_weights = None):
        """Compute a pivot table of agregated values casted along specified index and columns.

        Args:
            aggfunc(str, optional): Aggregation function, defaults to 'mean'
            columns(list, optional): Variable(s) in columns, defaults to None
            difference(bool, optional): Compute difference, defaults to False
            filter_by(str, optional): Boolean variable to filter by, defaults to None
            index(list, optional): Variable(s) in index (lines), defaults to None
            period(Period, optional): Period, defaults to None
            simulation(str, optional): Simulation to use
            baseline_simulation(str, optional): Baseline simulation to use when computing a difference
            use_baseline_for_columns(bool, optional): Use columns from baseline columns values, defaults to None
            values(list, optional): Aggregated variable(s) within cells, defaults to None
            missing_variable_default_value(float, optional): Default value for missing variables, defaults to np.nan
            concat_axis(int, optional): Axis to concatenate along (index = 0, columns = 1), defaults to None
            weighted(bool, optional): Whether to weight te aggregates (Default value = True)
            alternative_weights(str or int or float, optional): Weight variable name or numerical value. Use Simulation's weight_variable_by_entity if None, and if the later is None uses 1 ((Default value = None)

        Returns:
            pd.DataFrame: Pivot table

        """
        assert (not difference) or (baseline_simulation is not None), "Can't have difference when not baseline simulation"

        simulation = self.simulations[simulation]
        if baseline_simulation:
            baseline_simulation = self.simulations[baseline_simulation]

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

    def compute_winners_loosers(self, variable,
            simulation,
            baseline_simulation = None,
            filter_by = None,
            period = None,
            absolute_minimal_detected_variation = 0,
            relative_minimal_detected_variation = .01,
            observations_threshold = None,
            weighted = True,
            alternative_weights = None):

        simulation = self.simulations[simulation]
        if baseline_simulation:
            baseline_simulation = self.simulations[baseline_simulation]

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
            period = None, simulation = None, merge = False):
        """Create dataframe(s) of computed variable for every entity (eventually merged in a unique dataframe).

        Args:
          variables(list, optional): Variable to compute, defaults to None
          expressions(str, optional): Expressions to compute, defaults to None
          filter_by(str, optional): Boolean variable or expression, defaults to None
          index(bool, optional): Index by entity id, defaults to False
          period(Period, optional): Period, defaults to None
          simulation(str, optional): Simulation to use
          merge(bool, optional): Merge all the entities in one data frame, defaults to False

        Returns:
          dict or pandas.DataFrame: Dictionnary of dataframes by entities or dataframe with all the computed variables

        """
        if simulation is None:
            assert len(self.simulations.keys()) == 1
            simulation = list(self.simulations.values())[0]
        else:
            simulation = self.simulations[simulation]

        return simulation.create_data_frame_by_entity(
            variables = variables,
            expressions = expressions,
            filter_by = filter_by,
            index = index,
            period = period,
            merge = merge,
            )

    def custom_input_data_frame(self, input_data_frame, **kwargs):
        """Customize input data frame.

        Args:
          input_data_frame: original input data frame.
          kwargs: keyword arguments.
        """
        pass

    def dump_data_frame_by_entity(self, variables = None, survey_collection = None, survey_name = None):
        assert survey_collection is not None
        assert survey_name is not None
        assert variables is not None
        openfisca_data_frame_by_entity = self.create_data_frame_by_entity(variables = variables)
        for entity_key, data_frame in openfisca_data_frame_by_entity.items():
            survey = Survey(name = survey_name)
            survey.insert_table(name = entity_key, data_frame = data_frame)
            survey_collection.surveys.append(survey)
            survey_collection.dump(collection = "openfisca")

    def dump_simulations(self, directory: str):
        """
        Dump simulations.

        Args:
            directory (str, optional): Dump directory
        """
        assert directory is not None
        use_sub_directories = True if len(self.simulations) >= 2 else False

        if use_sub_directories:
            for simulation_name, simulation in self.simulations.items():
                dump_simulation(simulation, directory = os.path.join(directory, simulation_name))
        else:
            assert len(self.simulations.keys()) == 1
            simulation = list(self.simulations.values())[0]
            dump_simulation(simulation, directory)

    def generate_performance_data(self, output_dir: str):
        if not self.trace:
            raise ValueError("Method generate_performance_data cannot be used if trace hasn't been activated.")

        for simulation_name, simulation in self.simulations.items():
            simulation_dir = os.path.join(output_dir, f"{simulation_name}_perf_log")
            if not os.path.exists(output_dir):
                os.mkdir(output_dir)
            if not os.path.exists(simulation_dir):
                os.mkdir(simulation_dir)
            simulation.tracer.generate_performance_graph(simulation_dir)
            simulation.tracer.generate_performance_tables(simulation_dir)

    def inflate(self, inflator_by_variable = None, period = None, target_by_variable = None):
        assert inflator_by_variable or target_by_variable
        assert period is not None
        inflator_by_variable = dict() if inflator_by_variable is None else inflator_by_variable
        target_by_variable = dict() if target_by_variable is None else target_by_variable
        self.inflator_by_variable = inflator_by_variable
        self.target_by_variable = target_by_variable

        for _, simulation in self.simulations.items():
            simulation.inflate(inflator_by_variable, period, target_by_variable)

    def init_from_data(self, calibration_kwargs = None, inflation_kwargs = None,
            rebuild_input_data = False, rebuild_kwargs = None, data = None, memory_config = None, use_marginal_tax_rate = False):
        """Initialise a survey scenario from data.

        Args:
          rebuild_input_data(bool):  Whether or not to clean, format and save data. Take a look at :func:`build_input_data`
          data(dict): Contains the data, or metadata needed to know where to find it.
          use_marginal_tax_rate(bool): True to go into marginal effective tax rate computation mode.
          calibration_kwargs(dict):  Calibration options (Default value = None)
          inflation_kwargs(dict): Inflations options (Default value = None)
          rebuild_input_data(bool): Whether to rebuild the data (Default value = False)
          rebuild_kwargs:  Rebuild options (Default value = None)
        """
        # When not ``None``, it'll try to get the data for *period*.
        if data is not None:
            data_year = data.get("data_year", self.period)

        # When ``True`` it'll assume it is raw data and do all that described supra.
        # When ``False``, it'll assume data is ready for consumption.
        if rebuild_input_data:
            if rebuild_kwargs is not None:
                self.build_input_data(year = data_year, **rebuild_kwargs)
            else:
                self.build_input_data(year = data_year)

        debug = self.debug
        trace = self.trace

        if use_marginal_tax_rate:
            for name, tax_benefit_system in self.tax_benefit_systems.items():
                assert self.varying_variable in tax_benefit_system.variables, f"Variable {self.varying_variable} is not present tax benefit system named {name}"

        # Inverting reform and baseline because we are more likely
        # to use baseline input in reform than the other way around
        self.simulations = dict()
        for simulation_name, _ in self.tax_benefit_systems.items():
            self.new_simulation(simulation_name, debug = debug, data = data, trace = trace, memory_config = memory_config)
            if use_marginal_tax_rate:
                self.new_simulation(simulation_name, debug = debug, data = data, trace = trace, memory_config = memory_config, marginal_tax_rate_only = True)

        if calibration_kwargs is not None:
            assert set(calibration_kwargs.keys()).issubset(set(
                ['target_margins_by_variable', 'parameters', 'target_entity_count', 'other_entity_count', 'entity']))

        if inflation_kwargs is not None:
            assert set(inflation_kwargs.keys()).issubset(set(['inflator_by_variable', 'target_by_variable', 'period']))

        if calibration_kwargs:
            self.calibrate(**calibration_kwargs)

        if inflation_kwargs:
            self.inflate(**inflation_kwargs)

    def new_simulation(self, simulation_name, debug = False, trace = False, data = None, memory_config = None, marginal_tax_rate_only = False):
        tax_benefit_system = self.tax_benefit_systems[simulation_name]
        assert tax_benefit_system is not None

        period = periods.period(self.period)

        if 'custom_initialize' in dir(self):
            custom_initialize = (
                None
                if marginal_tax_rate_only
                else self.custom_initialize
                )
        else:
            custom_initialize = None

        data["collection"] = self.collection
        data["id_variable_by_entity_key"] = self.id_variable_by_entity_key
        data["role_variable_by_entity_key"] = self.role_variable_by_entity_key
        data["used_as_input_variables"] = self.used_as_input_variables

        simulation = Simulation.new_from_tax_benefit_system(
            tax_benefit_system = tax_benefit_system,
            debug = debug,
            trace = trace,
            data = data,
            memory_config = memory_config,
            period = period,
            custom_initialize = custom_initialize,
            )

        if marginal_tax_rate_only:
            self._apply_modification(simulation, period)
            if custom_initialize:
                custom_initialize(simulation)
            self.simulations[f"_modified_{simulation_name}"] = simulation
        else:
            self.simulations[simulation_name] = simulation

        simulation.weight_variable_by_entity = self.weight_variable_by_entity

        if self.period is not None:
            simulation.period = periods.period(self.period)

        return simulation

    def memory_usage(self):
        """Print memory usage."""
        for simulation_name, simulation in self.simulations.items():
            print(f"simulation : {simulation_name}")  # noqa analysis:ignore
            simulation.print_memory_usage()

    def neutralize_variables(self, tax_benefit_system):
        """Neutralizes input variables not in input dataframe and keep some crucial variables.

        Args:
          tax_benefit_system: The TaxBenefitSystem variables belongs to

        """
        for variable_name, variable in tax_benefit_system.variables.items():
            if variable.formulas:
                continue
            if self.used_as_input_variables and (variable_name in self.used_as_input_variables):
                continue
            if self.non_neutralizable_variables and (variable_name in self.non_neutralizable_variables):
                continue
            if self.weight_variable_by_entity and variable_name in list(self.weight_variable_by_entity.values()):
                continue

            tax_benefit_system.neutralize_variable(variable_name)

    def restore_simulations(self, directory, **kwargs):
        """Restores SurveyScenario's simulations.

        Args:
          directory: Directory to restore simulations from
          kwargs: Restoration options

        """
        assert os.path.exists(directory), "Cannot restore simulations from non existent directory"
        use_sub_directories = True if len(self.tax_benefit_systems) >= 2 else False

        self.simulations = dict()
        if use_sub_directories:
            for simulation_name, tax_benefit_system in self.tax_benefit_systems.items():
                simulation = restore_simulation(
                    os.path.join(directory, simulation_name),
                    tax_benefit_system,
                    **kwargs)
                simulation.id_variable_by_entity_key = self.id_variable_by_entity_key
                self.simulations[simulation_name] = simulation
        else:
            simulation = restore_simulation(directory, list(self.tax_benefit_systems.values())[0], **kwargs)
            simulation.id_variable_by_entity_key = self.id_variable_by_entity_key
            self.simulations["unique_simulation"] = simulation

    def set_input_data_frame(self, input_data_frame):
        """Set the input dataframe.

        Args:
          input_data_frame (pd.DataFrame): Input data frame

        """
        self.input_data_frame = input_data_frame

    def set_tax_benefit_systems(self, tax_benefit_systems: Dict[str, TaxBenefitSystem]):
        """
        Set the tax and benefit systems of the scenario.

        Args:
            tax_benefit_systems (Dict[str, TaxBenefitSystem]): The tax benefit systems
        """
        for tax_benefit_system in tax_benefit_systems.values():
            assert tax_benefit_system is not None
            if self.cache_blacklist is not None:
                tax_benefit_system.cache_blacklist = self.cache_blacklist
        #
        self.tax_benefit_systems = tax_benefit_systems

    def set_weight_variable_by_entity(self, weight_variable_by_entity = None):
        if weight_variable_by_entity is not None:
            self.weight_variable_by_entity = weight_variable_by_entity

        if self.simulations is not None:
            for simulation in self.simulations.values():
                simulation.set_weight_variable_by_entity(self.weight_variable_by_entity)

    def summarize_variable(self, variable = None, weighted = False, force_compute = False):
        """Print a summary of a variable including its memory usage for all the siulations.

        Args:
          variable(string): The variable being summarized
          weighted(bool): Whether the produced statistics should be weigthted or not
          force_compute(bool): Whether the computation of the variable should be forced

        Example:
            >>> from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario
            >>> survey_scenario = create_randomly_initialized_survey_scenario()
            >>> survey_scenario.summarize_variable(variable = "housing_occupancy_status", force_compute = True)
            <BLANKLINE>
            housing_occupancy_status: 1 periods * 5 cells * item size 2 (int16, default = HousingOccupancyStatus.tenant) = 10B
            Details:
            2017-01: owner = 0.00e+00 (0.0%), tenant = 5.00e+00 (100.0%), free_lodger = 0.00e+00 (0.0%), homeless = 0.00e+00 (0.0%).
            >>> survey_scenario.summarize_variable(variable = "rent", force_compute = True)
            <BLANKLINE>
            rent: 2 periods * 5 cells * item size 4 (float32, default = 0) = 40B
            Details:
            2017-01: mean = 562.385107421875, min = 156.01864624023438, max = 950.7142944335938, mass = 2.81e+03, default = 0.0%, median = 598.6585083007812
            2018-01: mean = 562.385107421875, min = 156.01864624023438, max = 950.7142944335938, mass = 2.81e+03, default = 0.0%, median = 598.6585083007812
            >>> survey_scenario.tax_benefit_systems["baseline"].neutralize_variable('age')
            >>> survey_scenario.summarize_variable(variable = "age")
            <BLANKLINE>
            age: neutralized variable (int64, default = 0)
        """
        for _simulation_name, simulation in self.simulations.items():
            simulation.summarize_variable(variable, weighted, force_compute)

    def _apply_modification(self, simulation, period):
        period = periods.period(period)
        varying_variable = self.varying_variable
        definition_period = simulation.tax_benefit_system.variables[varying_variable].definition_period

        def set_variable(varying_variable, varying_variable_value, period_):
            delta = self.variation_factor * varying_variable_value
            new_variable_value = varying_variable_value + delta
            simulation.delete_arrays(varying_variable, period_)
            simulation.set_input(varying_variable, period_, new_variable_value)

        if period.unit == definition_period:
            varying_variable_value = simulation.calculate(varying_variable, period = period)
            set_variable(varying_variable, varying_variable_value, period)

        elif (definition_period == MONTH) and (period.unit == YEAR and period.size_in_months == 12):
            varying_variable_value = simulation.calculate_add(varying_variable, period = period)
            for period_ in [periods.Period(('month', period.start.offset(month, 'month'), 1)) for month in range(12)]:
                set_variable(varying_variable, varying_variable_value / 12, period_)
        else:
            ValueError()
