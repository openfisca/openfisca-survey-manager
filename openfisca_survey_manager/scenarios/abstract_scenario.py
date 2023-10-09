"""Abstract survey scenario definition."""

from typing import Dict, List


import logging
import os
import numpy as np
import pandas as pd


from openfisca_core import periods
from openfisca_survey_manager.simulations import Simulation  # noqa analysis:ignore
from openfisca_core.simulation_builder import SimulationBuilder
from openfisca_core.indexed_enums import Enum
from openfisca_core.periods import MONTH, YEAR, ETERNITY
from openfisca_core.tools.simulation_dumper import dump_simulation, restore_simulation

from openfisca_survey_manager.calibration import Calibration
from openfisca_survey_manager import default_config_files_directory
from openfisca_survey_manager.survey_collections import SurveyCollection
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
    simulations = dict()
    target_by_variable = None  # variable total target to inflate to
    tax_benefit_systems = dict()
    trace = False
    used_as_input_variables = None
    used_as_input_variables_by_entity = None
    variation_factor = .03  # factor used to compute variation when estimating marginal tax rate
    varying_variable = None
    weight_variable_by_entity = None
    config_files_directory = default_config_files_directory

    def build_input_data(self, **kwargs):
        """Build input data."""
        NotImplementedError

    def calculate_series(self, variable, period = None, simulation = None):
        """Compute variable values for period and baseline or reform tax benefit and system.

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
        """Compute variable values for period and baseline or reform tax benefit and system.

        Args:
          variable(str, optional): Variable to compute
          period(Period, optional): Period, defaults to None
          simulation(str, optional): Simulation to use

        Returns:
          numpy.ndarray: Variable values

        """
        assert simulation is not None
        simulation = self.simulations[simulation]
        return simulation.adaptative_calculate_variable(variable, period = period)

    def calibrate(self, period: int = None, target_margins_by_variable: dict = None, parameters: dict = None, target_entity_count: float = None):
        """Calibrate the scenario data.

        Args:
            period (int, optionnal): Period of calibration. Defaults to scenario.year
            target_margins_by_variable (dict, optional): Variable targets margins. Defaults to None.
            parameters (dict, optional): Calibration parameters. Defaults to None.
            total_population (float, optional): Total population target. Defaults to None.
        """
        survey_scenario = self

        if period is None:
            assert survey_scenario.period is not None
            period = survey_scenario.period

        if parameters is not None:
            assert parameters['method'] in ['linear', 'raking ratio', 'logit'], \
                "Incorect parameter value: method should be 'linear', 'raking ratio' or 'logit'"
            if parameters['method'] == 'logit':
                assert parameters['invlo'] is not None
                assert parameters['up'] is not None
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
                parameters = parameters,
                # filter_by = self.filter_by,
                )
            calibration.calibrate(inplace = True)
            simulation.calibration = calibration

    def compute_aggregate(self, variable = None, aggfunc = 'sum', filter_by = None, period = None, simulation = None,
            baseline_simulation = None, missing_variable_default_value = np.nan, weighted = True, alternative_weights = None):
        """Compute variable aggregate.

        Args:
          variable: Variable (Default value = None)
          aggfunc: Aggregation function (Default value = 'sum')
          filter_by: Filtering variable (Default value = None)
          period: Period in which the variable is computed. If None, simulation.period is chosen (Default value = None)
          simulation(str, optional): Simulation to use
          baseline_simulation(str, optional): Baseline simulation to use when computing a difference
          missing_variable_default_value: Value of missing variable (Default value = np.nan)
          weighted: Whether to weight te aggregates (Default value = True)
          alternative_weights: Weight variable name or numerical value. Use SurveyScenario's weight_variable_by_entity if None, and if the latetr is None uses 1 ((Default value = None)

        Returns:
          float: Aggregate

        """
        assert aggfunc in ['count', 'mean', 'sum', 'count_non_zero']
        assert period is not None

        if baseline_simulation:
            return (
                self.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    simulation = simulation,
                    missing_variable_default_value = missing_variable_default_value,
                    weighted = weighted,
                    alternative_weights = alternative_weights,
                    )
                - self.compute_aggregate(
                    variable = variable,
                    aggfunc = aggfunc,
                    filter_by = filter_by,
                    period = period,
                    simulation = baseline_simulation,
                    missing_variable_default_value = missing_variable_default_value,
                    weighted = weighted,
                    alternative_weights = alternative_weights,
                    )
                )

        assert variable is not None
        simulation = self.simulations[simulation]
        assert simulation is not None, f"Missing {simulation} simulation"

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

    def compute_quantiles(self, variable = None, nquantiles = None, period = None, simulation = None, filter_by = None,
            weighted = True, alternative_weights = None):

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

    def compute_marginal_tax_rate(self, target_variable, period, simulation,
            value_for_zero_varying_variable = 0.0):
        """
        Compute marginal a rate of a target (MTR) with respect to a varying variable.

        Args:
            target_variable (str): the variable which marginal tax rate is computed
            period (Period): the period at which the the marginal tax rate is computed
            simulation(str, optional): Simulation to use
            value_for_zero_varying_variable (float, optional): value of MTR when the varying variable is zero. Defaults to 0.

        Returns:
            numpy.array: Vector of marginal rates
        """
        varying_variable = self.varying_variable
        simulation = self.simulations[simulation]

        assert self._modified_baseline_simulation is not None
        modified_simulation = self._modified_simulations[simulation]

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

    def compute_pivot_table(self, aggfunc = 'mean', columns = None, baseline_simulation = None, filter_by = None, index = None,
            period = None, simulation = None, use_baseline_for_columns = None, values = None,
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
        assert aggfunc in ['count', 'mean', 'sum']
        assert columns or index or values
        assert not (difference and use_baseline), "Can't have difference and use_baseline both set to True"

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
        # TODO: remove this method ?
        simulation = self.simulations[simulation]
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

    def dump_simulations(self, directory : str):
        """
        Dump simulations.

        Args:
            directory (str, optional): Dump directory
        """
        assert directory is not None
        use_sub_directories = True if len(self.simulations) >= 2 else False

        if use_sub_directories:
            for simulation_name, simulation in self.simulations.items():
                dump_simulation(directory = os.path.join(directory, simulation_name))
        else:
            dump_simulation(simulation, directory)

    def init_all_entities(self, tax_benefit_system, input_data_frame, builder, period = None):
        assert period is not None
        log.info('Initialasing simulation using input_data_frame for period {}'.format(period))

        if period.unit == YEAR:  # 1. year
            simulation = self.init_simulation_with_data_frame(
                tax_benefit_system,
                input_data_frame = input_data_frame,
                period = period,
                builder = builder,
                )
        elif period.unit == MONTH and period.size == 3:  # 2. quarter
            for offset in range(period.size):
                period_item = period.first_month.offset(offset, MONTH)
                simulation = self.init_simulation_with_data_frame(
                    tax_benefit_system,
                    input_data_frame = input_data_frame,
                    period = period_item,
                    builder = builder,
                    )
        elif period.unit == MONTH and period.size == 1:  # 3. months
            simulation = self.init_simulation_with_data_frame(
                tax_benefit_system,
                input_data_frame = input_data_frame,
                period = period,
                builder = builder,
                )
        else:
            raise ValueError("Invalid period {}".format(period))

        return simulation

    def filter_input_variables(self, input_data_frame = None):
        """Filter the input data frame from variables that won't be used or are set to be computed.

        Args:
          input_data_frame: Input dataframe (Default value = None)

        Returns:
          pd.DataFrame: filtered dataframe

        """
        assert input_data_frame is not None
        id_variable_by_entity_key = self.id_variable_by_entity_key
        role_variable_by_entity_key = self.role_variable_by_entity_key
        used_as_input_variables = self.used_as_input_variables

        tax_benefit_system = self.tax_benefit_system
        variables = tax_benefit_system.variables

        id_variables = [
            id_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]
        role_variables = [
            role_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]

        log.debug('Variable used_as_input_variables in filter: \n {}'.format(used_as_input_variables))

        unknown_columns = []
        for column_name in input_data_frame:
            if column_name in id_variables + role_variables:
                continue
            if column_name not in variables:
                unknown_columns.append(column_name)

        input_data_frame.drop(unknown_columns, axis = 1, inplace = True)

        if unknown_columns:
            log.debug('The following unknown columns {}, are dropped from input table'.format(
                sorted(unknown_columns)))

        used_columns = []
        dropped_columns = []
        for column_name in input_data_frame:
            if column_name in id_variables + role_variables:
                continue
            variable = variables[column_name]
            # Keeping the calculated variables that are initialized by the input data
            if variable.formulas:
                if column_name in used_as_input_variables:
                    used_columns.append(column_name)
                    continue

                dropped_columns.append(column_name)

        input_data_frame.drop(dropped_columns, axis = 1, inplace = True)

        if used_columns:
            log.debug(
                'These columns are not dropped because present in used_as_input_variables:\n {}'.format(
                    sorted(used_columns)))
        if dropped_columns:
            log.debug(
                'These columns in survey are set to be calculated, we drop them from the input table:\n {}'.format(
                    sorted(dropped_columns)))

        log.info('Keeping the following variables in the input_data_frame:\n {}'.format(
            sorted(list(input_data_frame.columns))))
        return input_data_frame

    def generate_performance_data(self, output_dir: str):
        if not self.trace:
            raise ValueError("Method generate_performance_data cannot be used if trace hasn't been activated.")

        for simulation_name, simulation in self.simulations.items():
            simulation_dir = os.path.join(output_dir, f"{simulation_name}_perf_log")
            if not os.path.exists(output_dir):
                os.mkdir(output_dir)
            if not os.path.exists(simulation_dir):
                os.mkdir(reform_dir)
            simulation.tracer.generate_performance_graph(simulation_dir)
            simulation.tracer.generate_performance_tables(simulation_dir)

    def inflate(self, inflator_by_variable = None, period = None, target_by_variable = None):
        assert inflator_by_variable or target_by_variable
        assert period is not None
        inflator_by_variable = dict() if inflator_by_variable is None else inflator_by_variable
        target_by_variable = dict() if target_by_variable is None else target_by_variable
        self.inflator_by_variable = inflator_by_variable
        self.target_by_variable = target_by_variable

        for simulation_name, simulation in self.simulations.items():
            tax_benefit_system = simulation.tax_benefit_system
            for variable_name in set(inflator_by_variable.keys()).union(set(target_by_variable.keys())):
                assert variable_name in tax_benefit_system.variables, \
                    "Variable {} is not a valid variable of the tax-benefit system".format(variable_name)
                if variable_name in target_by_variable:
                    inflator = inflator_by_variable[variable_name] = \
                        target_by_variable[variable_name] / self.compute_aggregate(
                            variable = variable_name, simulation = simulation_name, period = period)
                    log.info('Using {} as inflator for {} to reach the target {} '.format(
                        inflator, variable_name, target_by_variable[variable_name]))
                else:
                    assert variable_name in inflator_by_variable, 'variable_name is not in inflator_by_variable'
                    log.info('Using inflator {} for {}.  The target is thus {}'.format(
                        inflator_by_variable[variable_name],
                        variable_name, inflator_by_variable[variable_name] * self.compute_aggregate(
                            variable = variable_name, simulation = simulation_name, period = period)
                        ))
                    inflator = inflator_by_variable[variable_name]

                array = simulation.calculate_add(variable_name, period = period)
                assert array is not None
                simulation.delete_arrays(variable_name, period = period)  # delete existing arrays
                simulation.set_input(variable_name, period, inflator * array)  # insert inflated array

    def init_from_data(self, calibration_kwargs = None, inflation_kwargs = None,
            rebuild_input_data = False, rebuild_kwargs = None, data = None, memory_config = None, use_marginal_tax_rate = False,
            config_files_directory = default_config_files_directory):
        """Initialise a survey scenario from data.

        Args:
          rebuild_input_data(bool):  Whether or not to clean, format and save data. Take a look at :func:`build_input_data`
          data(dict): Contains the data, or metadata needed to know where to find it.
          use_marginal_tax_rate(bool): True to go into marginal effective tax rate computation mode.
          calibration_kwargs(dict):  Calibration options (Default value = None)
          inflation_kwargs(dict): Inflations options (Default value = None)
          rebuild_input_data(bool): Whether to rebuild the data (Default value = False)
          rebuild_kwargs:  Rebuild options (Default value = None)
          config_files_directory:  Directory where to find the configuration files (Default value = default_config_files_directory)
        """
        # When not ``None``, it'll try to get the data for *period*.
        if data is not None:
            data_year = data.get("data_year", self.period)

        self._set_id_variable_by_entity_key()
        self._set_role_variable_by_entity_key()
        self._set_used_as_input_variables_by_entity()

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
            assert self.varying_variable in self.tax_benefit_system.variables

        # Inverting reform and baseline because we are more likely
        # to use baseline input in reform than the other way around
        if self.baseline_tax_benefit_system is not None:
            self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config,
                use_baseline = True)
            if use_marginal_tax_rate:
                self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config, use_baseline = True,
                    marginal_tax_rate_only = True)

        # Note that I can pass a :class:`pd.DataFrame` directly, if I don't want to rebuild the data.
        self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config)

        if use_marginal_tax_rate:
            self.new_simulation(debug = debug, data = data, trace = trace, memory_config = memory_config, marginal_tax_rate_only = True)

        self.set_weight_variable_by_entity()

        if calibration_kwargs is not None:
            assert set(calibration_kwargs.keys()).issubset(set(
                ['target_margins_by_variable', 'parameters', 'total_population']))

        if inflation_kwargs is not None:
            assert set(inflation_kwargs.keys()).issubset(set(['inflator_by_variable', 'target_by_variable', 'period']))

        if calibration_kwargs:
            self.calibrate(**calibration_kwargs)

        if inflation_kwargs:
            self.inflate(**inflation_kwargs)

    def init_entity_structure(self, tax_benefit_system, entity, input_data_frame, builder):
        """Initialize sthe simulation with tax_benefit_system entities and input_data_frame.

        Args:
          tax_benefit_system(TaxBenfitSystem): The TaxBenefitSystem to get the structure from
          entity(Entity): The entity to initialize structure
          input_data_frame(pd.DataFrame): The input
          builder(Builder): The builder

        """
        id_variables = [
            self.id_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]
        role_variables = [
            self.role_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]

        if entity.is_person:
            for id_variable in id_variables + role_variables:
                assert id_variable in input_data_frame.columns, \
                    "Variable {} is not present in input dataframe".format(id_variable)

        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame)

        ids = range(len(input_data_frame))
        if entity.is_person:
            builder.declare_person_entity(entity.key, ids)
            for group_entity in tax_benefit_system.group_entities:
                _key = group_entity.key
                _id_variable = self.id_variable_by_entity_key[_key]
                _role_variable = self.role_variable_by_entity_key[_key]
                group_population = builder.declare_entity(_key, input_data_frame[_id_variable].drop_duplicates().sort_values().values)
                builder.join_with_persons(
                    group_population,
                    input_data_frame[_id_variable].astype('int').values,
                    input_data_frame[_role_variable].astype('int').values,
                    )

    def init_entity_data(self, entity, input_data_frame, period, simulation):
        used_as_input_variables = self.used_as_input_variables_by_entity[entity.key]
        diagnose_variable_mismatch(used_as_input_variables, input_data_frame)
        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame)

        for column_name, column_serie in input_data_frame.items():
            variable_instance = self.tax_benefit_system.variables.get(column_name)
            if variable_instance is None:
                continue

            if variable_instance.entity.key != entity.key:
                log.info("Ignoring variable {} which is not part of entity {} but {}".format(
                    column_name, entity.key, variable_instance.entity.key))
                continue
            init_variable_in_entity(simulation, entity.key, column_name, column_serie, period)

    def init_simulation_with_data_frame(self, tax_benefit_system, input_data_frame, period, builder):
        """Initialize the simulation period with current input_data_frame for an entity if specified."""
        used_as_input_variables = self.used_as_input_variables
        id_variable_by_entity_key = self.id_variable_by_entity_key
        role_variable_by_entity_key = self.role_variable_by_entity_key

        diagnose_variable_mismatch(used_as_input_variables, input_data_frame)

        id_variables = [
            id_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]
        role_variables = [
            role_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]

        for id_variable in id_variables + role_variables:
            assert id_variable in input_data_frame.columns, \
                "Variable {} is not present in input dataframe".format(id_variable)

        input_data_frame = self.filter_input_variables(input_data_frame = input_data_frame)

        index_by_entity_key = dict()

        for entity in tax_benefit_system.entities:
            self.init_entity_structure(tax_benefit_system, entity, input_data_frame, builder)

            if entity.is_person:
                continue

            else:
                index_by_entity_key[entity.key] = input_data_frame.loc[
                    input_data_frame[role_variable_by_entity_key[entity.key]] == 0,
                    id_variable_by_entity_key[entity.key]
                    ].sort_values().index

        for column_name, column_serie in input_data_frame.items():
            if role_variable_by_entity_key is not None:
                if column_name in role_variable_by_entity_key.values():
                    continue

            if id_variable_by_entity_key is not None:
                if column_name in id_variable_by_entity_key.values():
                    continue

            simulation = builder.build(tax_benefit_system)
            entity = tax_benefit_system.variables[column_name].entity
            if entity.is_person:
                init_variable_in_entity(simulation, entity.key, column_name, column_serie, period)
            else:
                init_variable_in_entity(simulation, entity.key, column_name, column_serie[index_by_entity_key[entity.key]], period)

        return simulation

    def new_simulation(self, debug = False, use_baseline = False, trace = False, data = None, memory_config = None, marginal_tax_rate_only = False):
        assert self.tax_benefit_system is not None
        tax_benefit_system = self.tax_benefit_system
        if self.baseline_tax_benefit_system is not None and use_baseline:
            tax_benefit_system = self.baseline_tax_benefit_system
        elif use_baseline:
            while True:
                baseline_tax_benefit_system = tax_benefit_system.baseline
                if isinstance(use_baseline, bool) and baseline_tax_benefit_system is None \
                        or baseline_tax_benefit_system == use_baseline:
                    break
                tax_benefit_system = baseline_tax_benefit_system

        period = periods.period(self.period)

        simulation = self.new_simulation_from_tax_benefit_system(
            tax_benefit_system = tax_benefit_system,
            debug = debug,
            trace = trace,
            data = data,
            memory_config = memory_config,
            period = period,
            skip_custom_initialize = marginal_tax_rate_only,  # Done after applying modifcation
            )

        if marginal_tax_rate_only:
            self._apply_modification(simulation, period)
            if not use_baseline:
                self._modified_simulation = simulation
            else:
                self._modified_baseline_simulation = simulation

            if 'custom_initialize' in dir(self):
                self.custom_initialize(simulation)

        else:
            if not use_baseline:
                self.simulation = simulation
            else:
                self.baseline_simulation = simulation

        return simulation

    def new_simulation_from_tax_benefit_system(self, tax_benefit_system = None, debug = False, trace = False, data = None, memory_config = None, period = None, skip_custom_initialize = False):
        assert tax_benefit_system is not None
        self.neutralize_variables(tax_benefit_system)
        #
        simulation = self.init_simulation(tax_benefit_system, period, data)
        simulation.debug = debug
        simulation.trace = trace
        simulation.opt_out_cache = True if self.cache_blacklist is not None else False
        simulation.memory_config = memory_config

        if (not skip_custom_initialize):
            if 'custom_initialize' in dir(self):
                self.custom_initialize(simulation)

        return simulation

    def init_simulation(self, tax_benefit_system, period, data):
        builder = SimulationBuilder()
        builder.create_entities(tax_benefit_system)

        data_year = data.get("data_year", self.period)
        survey = data.get('survey')

        default_source_types = [
            'input_data_frame',
            'input_data_table',
            'input_data_frame_by_entity',
            'input_data_frame_by_entity_by_period',
            'input_data_table_by_entity_by_period',
            'input_data_table_by_period',
            ]
        source_types = [
            source_type_
            for source_type_ in default_source_types
            if data.get(source_type_, None) is not None
            ]
        assert len(source_types) < 2, "There are too many data source types"
        assert len(source_types) >= 1, "There should be one data source type included in {}".format(
            default_source_types)
        source_type = source_types[0]
        source = data[source_type]

        if source_type == 'input_data_frame_by_entity':
            assert data_year is not None
            source_type = 'input_data_frame_by_entity_by_period'
            source = {periods.period(data_year): source}

        input_data_survey_prefix = data.get("input_data_survey_prefix") if data is not None else None

        if source_type == 'input_data_frame':
            simulation = self.init_all_entities(tax_benefit_system, source, builder, period)

        if source_type == 'input_data_table':
            # Case 1: fill simulation with a unique input_data_frame given by the attribute
            if input_data_survey_prefix is not None:
                openfisca_survey_collection = SurveyCollection.load(collection = self.collection)
                openfisca_survey = openfisca_survey_collection.get_survey("{}_{}".format(
                    input_data_survey_prefix, data_year))
                input_data_frame = openfisca_survey.get_values(table = "input").reset_index(drop = True)
            else:
                NotImplementedError

            self.custom_input_data_frame(input_data_frame, period = period)
            simulation = self.init_all_entities(tax_benefit_system, input_data_frame, builder, period)  # monolithic dataframes

        elif source_type == 'input_data_table_by_period':
            # Case 2: fill simulation with input_data_frame by period containing all entity variables
            for period, table in self.input_data_table_by_period.items():
                period = periods.period(period)
                log.debug('From survey {} loading table {}'.format(survey, table))
                input_data_frame = self.load_table(survey = survey, table = table)
                self.custom_input_data_frame(input_data_frame, period = period)
                simulation = self.init_all_entities(tax_benefit_system, input_data_frame, builder, period)  # monolithic dataframes

        elif source_type == 'input_data_frame_by_entity_by_period':
            for period, input_data_frame_by_entity in source.items():
                period = periods.period(period)
                for entity in tax_benefit_system.entities:
                    input_data_frame = input_data_frame_by_entity.get(entity.key)
                    if input_data_frame is None:
                        continue
                    self.custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                    self.init_entity_structure(tax_benefit_system, entity, input_data_frame, builder)

            simulation = builder.build(tax_benefit_system)
            for period, input_data_frame_by_entity in source.items():
                for entity in tax_benefit_system.entities:
                    input_data_frame = input_data_frame_by_entity.get(entity.key)
                    if input_data_frame is None:
                        log.debug("No input_data_frame found for entity {} at period {}".format(entity, period))
                        continue
                    self.custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                    self.init_entity_data(entity, input_data_frame, period, simulation)

        elif source_type == 'input_data_table_by_entity_by_period':
            # Case 3: fill simulation with input_data_table by entity_by_period containing a dictionnary
            # of all periods containing a dictionnary of entity variables
            input_data_table_by_entity_by_period = source
            simulation = None
            for period, input_data_table_by_entity in input_data_table_by_entity_by_period.items():
                period = periods.period(period)

                if simulation is None:
                    for entity in tax_benefit_system.entities:
                        table = input_data_table_by_entity.get(entity.key)
                        if table is None:
                            continue
                        if survey is not None:
                            input_data_frame = self.load_table(survey = survey, table = table)
                        else:
                            input_data_frame = self.load_table(survey = 'input', table = table)
                        self.custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                        self.init_entity_structure(tax_benefit_system, entity, input_data_frame, builder)

                    simulation = builder.build(tax_benefit_system)

                for entity in tax_benefit_system.entities:
                    table = input_data_table_by_entity.get(entity.key)
                    if table is None:
                        continue
                    if survey is not None:
                        input_data_frame = self.load_table(survey = survey, table = table)
                    else:
                        input_data_frame = self.load_table(survey = 'input', table = table)
                    self.custom_input_data_frame(input_data_frame, period = period, entity = entity.key)
                    self.init_entity_data(entity, input_data_frame, period, simulation)
        else:
            pass

        if self.period is not None:
            simulation.period = periods.period(self.period)

        simulation.weight_variable_by_entity = self.weight_variable_by_entity

        return simulation

    def load_table(self, variables = None, collection = None, survey = None,
            table = None):
        collection = collection or self.collection
        survey_collection = SurveyCollection.load(collection = self.collection, config_files_directory=self.config_files_directory)
        if survey is not None:
            survey = survey
        else:
            survey = "{}_{}".format(self.input_data_survey_prefix, str(self.period))
        survey_ = survey_collection.get_survey(survey)
        log.debug("Loading table {} in survey {} from collection {}".format(table, survey, collection))
        return survey_.get_values(table = table, variables = variables)

    def memory_usage(self):
        for simulation_name, simulation in self.simulations.items():
            print(f"simulation : {simulation_name}")
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
            if self.weight_variable_by_entity and (variable_name in self.weight_variable_by_entity.values()):
                continue

            tax_benefit_system.neutralize_variable(variable_name)

    def restore_simulations(self, directory, **kwargs):
        """Restores SurveyScenario's simulations.

        Args:
          directory: Directory to restore simulations from
          kwargs: Restoration options

        """
        assert os.path.exists(directory), "Cannot restore simulations from non existent directory"
        use_sub_directories = True if len(self.simulations) >= 2 else False

        if use_sub_directories:
            for simulation_name, simulation in self.simulations.items():
                restore_simulation(directory = os.path.join(directory, simulation_name), **kwargs)
        else:
            restore_simulation(directory = directory, **kwargs)


    def set_input_data_frame(self, input_data_frame):
        """Set the input dataframe.

        Args:
          input_data_frame (pd.DataFrame): Input data frame

        """
        self.input_data_frame = input_data_frame

    def set_tax_benefit_systems(self, tax_benefit_systems : dict):
        """Set the tax and benefit systems of the scenario.

        Args:
          tax_benefit_systems:
        """
        for tax_benefit_system in tax_benefit_systems.values():
            assert tax_benefit_system is not None
            if self.cache_blacklist is not None:
                tax_benefit_system.cache_blacklist = self.cache_blacklist

    def set_weight_variable_by_entity(self, weight_variable_by_entity = None):
        if weight_variable_by_entity is not None:
            self.weight_variable_by_entity = weight_variable_by_entity

        for simulation in [self.simulation, self.baseline_simulation]:
            if simulation is not None:
                simulation.weight_variable_by_entity = self.weight_variable_by_entity

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
            >>> survey_scenario.tax_benefit_system.neutralize_variable('age')
            >>> survey_scenario.summarize_variable(variable = "age")
            <BLANKLINE>
            age: neutralized variable (int64, default = 0)
        """
        for simulation_name, simulation in self.simulations.items():
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

    def _set_id_variable_by_entity_key(self) -> Dict[str, str]:
        """Identify and sets the correct ids for the different entities."""
        if self.id_variable_by_entity_key is None:
            log.debug("Use default id_variable names")
            self.id_variable_by_entity_key = dict(
                (entity.key, entity.key + '_id') for entity in self.tax_benefit_system.entities)

        return self.id_variable_by_entity_key

    def _set_role_variable_by_entity_key(self) -> Dict[str, str]:
        """Identify and sets the correct roles for the different entities."""
        if self.role_variable_by_entity_key is None:
            self.role_variable_by_entity_key = dict(
                (entity.key, entity.key + '_role_index') for entity in self.tax_benefit_system.entities)

        return self.role_variable_by_entity_key

    def _set_used_as_input_variables_by_entity(self) -> Dict[str, List[str]]:
        """Identify and sets the correct input variables for the different entities."""
        if self.used_as_input_variables_by_entity is not None:
            return

        tax_benefit_system = self.tax_benefit_system

        assert set(self.used_as_input_variables) <= set(tax_benefit_system.variables.keys()), \
            "Some variables used as input variables are not part of the tax benefit system:\n {}".format(
                set(self.used_as_input_variables).difference(set(tax_benefit_system.variables.keys()))
                )

        self.used_as_input_variables_by_entity = dict()

        for entity in tax_benefit_system.entities:
            self.used_as_input_variables_by_entity[entity.key] = [
                variable
                for variable in self.used_as_input_variables
                if tax_benefit_system.get_variable(variable).entity.key == entity.key
                ]

        return self.used_as_input_variables_by_entity


# Helpers

def init_variable_in_entity(simulation, entity, variable_name, series, period):
    variable = simulation.tax_benefit_system.variables[variable_name]

    # np.issubdtype cannot handles categorical variables
    if (not pd.api.types.is_categorical_dtype(series)) and np.issubdtype(series.values.dtype, np.floating):
        if series.isnull().any():
            log.debug('There are {} NaN values for {} non NaN values in variable {}'.format(
                series.isnull().sum(), series.notnull().sum(), variable_name))
            log.debug('We convert these NaN values of variable {} to {} its default value'.format(
                variable_name, variable.default_value))
            series.fillna(variable.default_value, inplace = True)
        assert series.notnull().all(), \
            'There are {} NaN values for {} non NaN values in variable {}'.format(
                series.isnull().sum(), series.notnull().sum(), variable_name)

    enum_variable_imputed_as_enum = (
        variable.value_type == Enum
        and (
            pd.api.types.is_categorical_dtype(series)
            or not (
                np.issubdtype(series.values.dtype, np.integer)
                or np.issubdtype(series.values.dtype, float)
                )
            )
        )

    if enum_variable_imputed_as_enum:
        if series.isnull().any():
            log.debug('There are {} NaN values ({}% of the array) in variable {}'.format(
                series.isnull().sum(), series.isnull().mean() * 100, variable_name))
            log.debug('We convert these NaN values of variable {} to {} its default value'.format(
                variable_name, variable.default_value._name_))
            series.fillna(variable.default_value._name_, inplace = True)
        possible_values = variable.possible_values
        index_by_category = dict(zip(
            possible_values._member_names_,
            range(len(possible_values._member_names_))
            ))
        series.replace(index_by_category, inplace = True)

    if series.values.dtype != variable.dtype:
        log.debug(
            'Converting {} from dtype {} to {}'.format(
                variable_name, series.values.dtype, variable.dtype)
            )

    array = series.values.astype(variable.dtype)
    # TODO is the next line needed ?
    # Might be due to values returning also ndarray like objects
    # for instance for categories or
    np_array = np.array(array, dtype = variable.dtype)
    if variable.definition_period == YEAR and period.unit == MONTH:
        # Some variables defined for a year are present in month/quarter dataframes
        # Cleaning the dataframe would probably be better in the long run
        log.warn('Trying to set a monthly value for variable {}, which is defined on a year. The  montly values you provided will be summed.'
            .format(variable_name).encode('utf-8'))

        if simulation.get_array(variable_name, period.this_year) is not None:
            array_sum = simulation.get_array(variable_name, period.this_year) + np_array
            simulation.set_input(variable_name, period.this_year, array_sum)
        else:
            simulation.set_input(variable_name, period.this_year, np_array)

    else:
        simulation.set_input(variable_name, period, np_array)


def diagnose_variable_mismatch(used_as_input_variables, input_data_frame):
    """Diagnose variables mismatch.

    Args:
      used_as_input_variables(lsit): List of variable to test presence
      input_data_frame: DataFrame in which to test variables presence

    """
    variables_mismatch = set(used_as_input_variables).difference(set(input_data_frame.columns)) if used_as_input_variables else None
    if variables_mismatch:
        log.info(
            'The following variables are used as input variables are not present in the input data frame: \n {}'.format(
                sorted(variables_mismatch)))
    if variables_mismatch:
        log.debug('The following variables are used as input variables: \n {}'.format(
            sorted(used_as_input_variables)))
        log.debug('The input_data_frame contains the following variables: \n {}'.format(
            sorted(list(input_data_frame.columns))))
