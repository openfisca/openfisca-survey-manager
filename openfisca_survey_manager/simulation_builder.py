import logging
from typing import Dict, List

from openfisca_core.model_api import MONTH, YEAR
from openfisca_core.simulations.simulation_builder import SimulationBuilder


SimulationBuilder.id_variable_by_entity_key = None
SimulationBuilder.role_variable_by_entity_key = None
SimulationBuilder.used_as_input_variables = None
SimulationBuilder.used_as_input_variables_by_entity = None


log = logging.getLogger(__name__)


# Helpers

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


# SimulationBuilder monkey-patched methods

def _set_id_variable_by_entity_key(builder) -> Dict[str, str]:
    """Identify and sets the correct ids for the different entities."""
    if builder.id_variable_by_entity_key is None:
        log.debug("Use default id_variable names")
        builder.id_variable_by_entity_key = dict(
            (entity.key, entity.key + '_id') for entity in builder.tax_benefit_system.entities)

    return builder.id_variable_by_entity_key


def _set_role_variable_by_entity_key(builder) -> Dict[str, str]:
    """Identify and sets the correct roles for the different entities."""
    if builder.role_variable_by_entity_key is None:
        builder.role_variable_by_entity_key = dict(
            (entity.key, entity.key + '_role_index') for entity in builder.tax_benefit_system.entities)

    return builder.role_variable_by_entity_key


def _set_used_as_input_variables_by_entity(builder) -> Dict[str, List[str]]:
    """Identify and sets the correct input variables for the different entities."""
    if builder.used_as_input_variables_by_entity is not None:
        return

    tax_benefit_system = builder.tax_benefit_system

    assert set(builder.used_as_input_variables) <= set(tax_benefit_system.variables.keys()), \
        "Some variables used as input variables are not part of the tax benefit system:\n {}".format(
            set(builder.used_as_input_variables).difference(set(tax_benefit_system.variables.keys()))
            )

    builder.used_as_input_variables_by_entity = dict()

    for entity in tax_benefit_system.entities:
        builder.used_as_input_variables_by_entity[entity.key] = [
            variable
            for variable in builder.used_as_input_variables
            if tax_benefit_system.get_variable(variable).entity.key == entity.key
            ]

    return builder.used_as_input_variables_by_entity


def filter_input_variables(builder, input_data_frame, tax_benefit_system):
    """Filter the input data frame from variables that won't be used or are set to be computed.

    Args:
        input_data_frame: Input dataframe (Default value = None)

    Returns:
        pd.DataFrame: filtered dataframe

    """
    assert input_data_frame is not None
    id_variable_by_entity_key = builder.id_variable_by_entity_key
    role_variable_by_entity_key = builder.role_variable_by_entity_key
    used_as_input_variables = builder.used_as_input_variables

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


def init_all_entities(builder, input_data_frame, period = None):
    assert period is not None
    log.info('Initialasing simulation using input_data_frame for period {}'.format(period))
    builder._set_id_variable_by_entity_key()
    builder._set_role_variable_by_entity_key()

    if period.unit == YEAR:  # 1. year
        simulation = builder.init_simulation_with_data_frame(
            input_data_frame = input_data_frame,
            period = period,
            )
    elif period.unit == MONTH and period.size == 3:  # 2. quarter
        for offset in range(period.size):
            period_item = period.first_month.offset(offset, MONTH)
            simulation = builder.init_simulation_with_data_frame(
                input_data_frame = input_data_frame,
                period = period_item,
                )
    elif period.unit == MONTH and period.size == 1:  # 3. months
        simulation = builder.init_simulation_with_data_frame(
            input_data_frame = input_data_frame,
            period = period,
            )
    else:
        raise ValueError("Invalid period {}".format(period))

    simulation.id_variable_by_entity_key = builder.id_variable_by_entity_key
    return simulation


def init_entity_structure(builder, entity, input_data_frame):
    """Initialize sthe simulation with tax_benefit_system entities and input_data_frame.

    Args:
        tax_benefit_system(TaxBenfitSystem): The TaxBenefitSystem to get the structure from
        entity(Entity): The entity to initialize structure
        input_data_frame(pd.DataFrame): The input
        builder(Builder): The builder

    """
    tax_benefit_system = builder.tax_benefit_system
    builder._set_id_variable_by_entity_key()
    builder._set_role_variable_by_entity_key()
    builder._set_used_as_input_variables_by_entity()

    input_data_frame = builder.filter_input_variables(input_data_frame, tax_benefit_system)

    id_variables = [
        builder.id_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]
    role_variables = [
        builder.role_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]

    if entity.is_person:
        for id_variable in id_variables + role_variables:
            assert id_variable in input_data_frame.columns, \
                "Variable {} is not present in input dataframe".format(id_variable)

    ids = range(len(input_data_frame))
    if entity.is_person:
        builder.declare_person_entity(entity.key, ids)
        for group_entity in tax_benefit_system.group_entities:
            _key = group_entity.key
            _id_variable = builder.id_variable_by_entity_key[_key]
            _role_variable = builder.role_variable_by_entity_key[_key]
            group_population = builder.declare_entity(_key, input_data_frame[_id_variable].drop_duplicates().sort_values().values)
            builder.join_with_persons(
                group_population,
                input_data_frame[_id_variable].astype('int').values,
                input_data_frame[_role_variable].astype('int').values,
                )


def init_simulation_with_data_frame(builder, input_data_frame, period):
    """Initialize the simulation period with current input_data_frame for an entity if specified."""
    used_as_input_variables = builder.used_as_input_variables
    id_variable_by_entity_key = builder.id_variable_by_entity_key
    role_variable_by_entity_key = builder.role_variable_by_entity_key
    tax_benefit_system = builder.tax_benefit_system
    assert tax_benefit_system is not None

    diagnose_variable_mismatch(used_as_input_variables, input_data_frame)

    id_variables = [
        id_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]
    role_variables = [
        role_variable_by_entity_key[_entity.key] for _entity in tax_benefit_system.group_entities]

    for id_variable in id_variables + role_variables:
        assert id_variable in input_data_frame.columns, \
            "Variable {} is not present in input dataframe".format(id_variable)

    input_data_frame = builder.filter_input_variables(input_data_frame, tax_benefit_system)

    index_by_entity_key = dict()

    for entity in tax_benefit_system.entities:
        builder.init_entity_structure(entity, input_data_frame)

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
            simulation.init_variable_in_entity(entity.key, column_name, column_serie, period)
        else:
            simulation.init_variable_in_entity(entity.key, column_name, column_serie[index_by_entity_key[entity.key]], period)

    assert builder.id_variable_by_entity_key is not None
    simulation.id_variable_by_entity_key = builder.id_variable_by_entity_key
    return simulation


SimulationBuilder._set_id_variable_by_entity_key = _set_id_variable_by_entity_key
SimulationBuilder._set_role_variable_by_entity_key = _set_role_variable_by_entity_key
SimulationBuilder._set_used_as_input_variables_by_entity = _set_used_as_input_variables_by_entity
SimulationBuilder.filter_input_variables = filter_input_variables
SimulationBuilder.init_all_entities = init_all_entities
SimulationBuilder.init_entity_structure = init_entity_structure
SimulationBuilder.init_simulation_with_data_frame = init_simulation_with_data_frame
