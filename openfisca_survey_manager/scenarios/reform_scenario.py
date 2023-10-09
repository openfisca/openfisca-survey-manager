"""Abstract survey scenario definition."""

import logging
import numpy as np
import pandas as pd


from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario, diagnose_variable_mismatch, init_variable_in_entity
# from openfisca_core import periods
# from openfisca_survey_manager.simulations import Simulation  # noqa analysis:ignore
# from openfisca_core.simulation_builder import SimulationBuilder
# from openfisca_core.indexed_enums import Enum
# from openfisca_core.periods import MONTH, YEAR, ETERNITY
# from openfisca_core.tools.simulation_dumper import dump_simulation, restore_simulation

# from openfisca_survey_manager.calibration import Calibration
from openfisca_survey_manager import default_config_files_directory
# from openfisca_survey_manager.survey_collections import SurveyCollection
# from openfisca_survey_manager.surveys import Survey

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

    # def calibrate(self, period: int = None, target_margins_by_variable: dict = None, parameters: dict = None, target_entity_count: float = None):
    #     """Calibrate the scenario data.

    #     Args:
    #         period (int, optionnal): Period of calibration. Defaults to scenario.year
    #         target_margins_by_variable (dict, optional): Variable targets margins. Defaults to None.
    #         parameters (dict, optional): Calibration parameters. Defaults to None.
    #         total_population (float, optional): Total population target. Defaults to None.
    #     """
    #     survey_scenario = self

    #     if period is None:
    #         assert survey_scenario.period is not None
    #         period = survey_scenario.period

    #     if parameters is not None:
    #         assert parameters['method'] in ['linear', 'raking ratio', 'logit'], \
    #             "Incorect parameter value: method should be 'linear', 'raking ratio' or 'logit'"
    #         if parameters['method'] == 'logit':
    #             assert parameters['invlo'] is not None
    #             assert parameters['up'] is not None
    #     else:
    #         parameters = dict(method = 'logit', up = 3, invlo = 3)

    #     # TODO: filtering using filtering_variable_by_entity
    #     for simulation in [survey_scenario.simulation, survey_scenario.baseline_simulation]:
    #         if simulation is None:
    #             continue
    #         calibration = Calibration(
    #             simulation,
    #             target_margins_by_variable,
    #             period,
    #             target_entity_count = target_entity_count,
    #             parameters = parameters,
    #             # filter_by = self.filter_by,
    #             )
    #         calibration.calibrate(inplace = True)
    #         simulation.calibration = calibration

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

    def custom_input_data_frame(self, input_data_frame, **kwargs):
        """Customize input data frame.

        Args:
          input_data_frame: original input data frame.
          kwargs: keyword arguments.
        """
        pass

    def inflate(self, inflator_by_variable = None, period = None, target_by_variable = None):
        assert inflator_by_variable or target_by_variable
        assert period is not None
        inflator_by_variable = dict() if inflator_by_variable is None else inflator_by_variable
        target_by_variable = dict() if target_by_variable is None else target_by_variable
        self.inflator_by_variable = inflator_by_variable
        self.target_by_variable = target_by_variable

        assert self.simulation is not None
        for use_baseline in [False, True]:
            if use_baseline:
                simulation = self.baseline_simulation
            else:
                assert self.simulation is not None
                simulation = self.simulation
                if (self.simulation == self.baseline_simulation):  # Avoid inflating two times
                    continue

            if simulation is None:
                continue

            tax_benefit_system = self.tax_benefit_system
            for variable_name in set(inflator_by_variable.keys()).union(set(target_by_variable.keys())):
                assert variable_name in tax_benefit_system.variables, \
                    "Variable {} is not a valid variable of the tax-benefit system".format(variable_name)
                if variable_name in target_by_variable:
                    inflator = inflator_by_variable[variable_name] = \
                        target_by_variable[variable_name] / self.compute_aggregate(
                            variable = variable_name, use_baseline = use_baseline, period = period)
                    log.info('Using {} as inflator for {} to reach the target {} '.format(
                        inflator, variable_name, target_by_variable[variable_name]))
                else:
                    assert variable_name in inflator_by_variable, 'variable_name is not in inflator_by_variable'
                    log.info('Using inflator {} for {}.  The target is thus {}'.format(
                        inflator_by_variable[variable_name],
                        variable_name, inflator_by_variable[variable_name] * self.compute_aggregate(
                            variable = variable_name, use_baseline = use_baseline, period = period)
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

    # def memory_usage(self, use_baseline = False):
    #     if use_baseline:
    #         simulation = self.baseline_simulation
    #     else:
    #         simulation = self.simulation

    #     memory_usage_by_variable = simulation.get_memory_usage()['by_variable']
    #     try:
    #         usage_stats = simulation.tracer.usage_stats
    #     except AttributeError:
    #         log.warning("The simulation trace mode is not activated. You need to activate it to get stats about variable usage (hits).")
    #         usage_stats = None
    #     infos_lines = list()

    #     for variable, infos in memory_usage_by_variable.items():
    #         hits = usage_stats[variable]['nb_requests'] if usage_stats else None
    #         infos_lines.append((
    #             infos['total_nb_bytes'],
    #             variable, "{}: {} periods * {} cells * item size {} ({}) = {} with {} hits".format(
    #                 variable,
    #                 infos['nb_arrays'],
    #                 infos['nb_cells_by_array'],
    #                 infos['cell_size'],
    #                 infos['dtype'],
    #                 humanize.naturalsize(infos['total_nb_bytes'], gnu = True),
    #                 hits,
    #                 )
    #             ))
    #     infos_lines.sort()
    #     for _, _, line in infos_lines:
    #         print(line.rjust(100))  # noqa analysis:ignore

    def set_input_data_frame(self, input_data_frame):
        """Set the input dataframe.

        Args:
          input_data_frame (pd.DataFrame): Input data frame

        """
        self.input_data_frame = input_data_frame

    def set_weight_variable_by_entity(self, weight_variable_by_entity = None):
        if weight_variable_by_entity is not None:
            self.weight_variable_by_entity = weight_variable_by_entity

        for simulation in [self.simulation, self.baseline_simulation]:
            if simulation is not None:
                simulation.weight_variable_by_entity = self.weight_variable_by_entity
