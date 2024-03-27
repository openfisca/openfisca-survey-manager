import logging
import os
import pandas as pd


from openfisca_core import periods
from openfisca_core.parameters import ParameterNode, Scale
from typing import List, Optional
from openfisca_survey_manager.survey_collections import SurveyCollection

log = logging.getLogger(__name__)


def do_nothing(*args, **kwargs):
    return None


def inflate_parameters(parameters, inflator, base_year, last_year = None, ignore_missing_units = False,
                       start_instant = None, round_ndigits = 2):
    """
    Inflate a Parameter node or a Parameter lead according for the years between base_year and last_year
    ::parameters:: af Parameter node or a Parameter leaf
    ::inflator:: rate used to inflate the parameter. The rate is unique for all the years
    ::base_year:: base year of the parameter
    ::last_year::  last year of inflation
    ::ignore_missing_units:: if True, a parameter leaf without unit in metadata will not be inflate
    ::start_instant :: Instant of the year when the update should start, if None will be Junuary 1st
    ::round_ndigits:: Number of digits to keep in the rounded result
    """

    if (last_year is not None) and (last_year > base_year + 1):
        for year in range(base_year + 1, last_year + 1):  # For each year we inflate with the same inflator rate. Example : base_year + 1 : paramaters = paramaters * inflator ; base_year + 2 : parameters = parameters * inflator * inflator
            inflate_parameters(parameters, inflator, year - 1, last_year = year, ignore_missing_units = ignore_missing_units,
                               start_instant = start_instant, round_ndigits = round_ndigits)

    else:
        if last_year is None:
            last_year = base_year + 1

        assert last_year == base_year + 1

        if isinstance(parameters, ParameterNode):
            for sub_parameter in parameters.children.values():
                inflate_parameters(sub_parameter, inflator, base_year, last_year, ignore_missing_units = ignore_missing_units,
                                   start_instant = start_instant, round_ndigits = round_ndigits)
        else:
            acceptable_units = [
                'rate_unit',
                'threshold_unit',
                'unit',
                ]
            if ignore_missing_units:
                if not hasattr(parameters, 'metadata'):
                    return
                # Empty intersection: not unit present in metadata
                if not bool(set(parameters.metadata.keys()) & set(acceptable_units)):
                    return
            assert hasattr(parameters, 'metadata'), "{} doesn't have metadata".format(parameters.name)
            unit_types = set(parameters.metadata.keys()).intersection(set(acceptable_units))
            assert unit_types, "No admissible unit in metadata for parameter {}. You may consider using the option 'ignore_missing_units' from the inflate_paramaters() function.".format(
                parameters.name)
            if len(unit_types) > 1:
                assert unit_types == set(['threshold_unit', 'rate_unit']), \
                    "Too much admissible units in metadata for parameter {}".format(
                        parameters.name)
            unit_by_type = dict([
                (unit_type, parameters.metadata[unit_type]) for unit_type in unit_types
                ])
            for unit_type in unit_by_type.keys():
                if parameters.metadata[unit_type].startswith("currency"):
                    inflate_parameter_leaf(parameters, base_year, inflator, unit_type = unit_type, start_instant = start_instant, round_ndigits = round_ndigits)


def inflate_parameter_leaf(sub_parameter, base_year, inflator, unit_type = 'unit', start_instant = None, round_ndigits = 2):
    """
    Inflate a Parameter leaf according to unit type for the year after base_year
    ::sub_parameter:: af Parameter leaf
    ::base_year:: base year of the parameter
    ::inflator:: rate used to inflate the parameter
    ::unit_type:: unit supposed by default. Other admissible unit types are threshold_unit and rate_unit
    ::start_instant:: Instant of the year when the update should start, if None will be Junuary 1st
    ::round_ndigits:: Number of digits to keep in the rounded result
    """
    if isinstance(sub_parameter, Scale):
        if unit_type == 'threshold_unit':
            for bracket in sub_parameter.brackets:
                threshold = bracket.children['threshold']
                inflate_parameter_leaf(threshold, base_year, inflator, start_instant = start_instant, round_ndigits = round_ndigits)
            return
    else:
        # Remove new values for year > base_year
        kept_instants_str = [
            parameter_at_instant.instant_str
            for parameter_at_instant in sub_parameter.values_list
            if periods.instant(parameter_at_instant.instant_str).year <= base_year
            ]
        if not kept_instants_str:
            return

        last_admissible_instant_str = max(kept_instants_str)
        sub_parameter.update(
            start = last_admissible_instant_str,
            value = sub_parameter(last_admissible_instant_str)
            )
        if start_instant is not None:
            assert periods.instant(start_instant).year == (base_year + 1), "Year of start_instant should be base_year + 1"
            value = (
                round(sub_parameter("{}-12-31".format(base_year)) * (1 + inflator), round_ndigits)
                if sub_parameter("{}-12-31".format(base_year)) is not None
                else None
                )
            sub_parameter.update(
                start = start_instant,
                value = value,
                )
        else:
            restricted_to_base_year_value_list = [
                parameter_at_instant for parameter_at_instant in sub_parameter.values_list
                if periods.instant(parameter_at_instant.instant_str).year == base_year
                ]
            # When value is changed in the base year
            if restricted_to_base_year_value_list:
                for parameter_at_instant in reversed(restricted_to_base_year_value_list):
                    if parameter_at_instant.instant_str.startswith(str(base_year)):
                        value = (
                            round(parameter_at_instant.value * (1 + inflator), round_ndigits)
                            if parameter_at_instant.value is not None
                            else None
                            )
                        sub_parameter.update(
                            start = parameter_at_instant.instant_str.replace(
                                str(base_year), str(base_year + 1)
                                ),
                            value = value,
                            )
            # Or use the value at that instant even when it is defined earlier tahn the base year
            else:
                value = (
                    round(sub_parameter("{}-12-31".format(base_year)) * (1 + inflator), round_ndigits)
                    if sub_parameter("{}-12-31".format(base_year)) is not None
                    else None
                    )
                sub_parameter.update(
                    start = "{}-01-01".format(base_year + 1),
                    value = value,
                    )


def asof(tax_benefit_system, instant):
    parameters = tax_benefit_system.parameters
    parameters_asof(parameters, instant)
    variables_asof(tax_benefit_system, instant)


def leaf_asof(sub_parameter, instant):
    kept_instants_str = [
        parameter_at_instant.instant_str
        for parameter_at_instant in sub_parameter.values_list
        if periods.instant(parameter_at_instant.instant_str) <= instant
        ]
    if not kept_instants_str:
        sub_parameter.values_list = []
        return

    last_admissible_instant_str = max(kept_instants_str)
    sub_parameter.update(
        start = last_admissible_instant_str,
        value = sub_parameter(last_admissible_instant_str)
        )
    return


def parameters_asof(parameters, instant):
    if isinstance(instant, str):
        instant = periods.instant(instant)
    assert isinstance(instant, periods.Instant)

    for sub_parameter in parameters.children.values():
        if isinstance(sub_parameter, ParameterNode):
            parameters_asof(sub_parameter, instant)
        else:
            if isinstance(sub_parameter, Scale):
                for bracket in sub_parameter.brackets:
                    threshold = bracket.children['threshold']
                    rate = bracket.children.get('rate')
                    amount = bracket.children.get('amount')
                    leaf_asof(threshold, instant)
                    if rate:
                        leaf_asof(rate, instant)
                    if amount:
                        leaf_asof(amount, instant)
            else:
                leaf_asof(sub_parameter, instant)


def variables_asof(tax_benefit_system, instant, variables_list = None):
    if isinstance(instant, str):
        instant = periods.instant(instant)
    assert isinstance(instant, periods.Instant)

    if variables_list is None:
        variables_list = tax_benefit_system.variables.keys()

    for variable_name, variable in tax_benefit_system.variables.items():
        if variable_name in variables_list:
            formulas = variable.formulas
            for instant_str in list(formulas.keys()):
                if periods.instant(instant_str) > instant:
                    del formulas[instant_str]

            if variable.end is not None:
                if periods.instant(variable.end) >= instant:
                    variable.end = None


def stata_files_to_data_frames(data, period = None):
    assert period is not None
    period = periods.period(period)

    stata_file_by_entity = data.get('stata_file_by_entity')
    if stata_file_by_entity is None:
        return

    variables_from_stata_files = list()
    input_data_frame_by_entity_by_period = dict()
    input_data_frame_by_entity_by_period[periods.period(period)] = input_data_frame_by_entity = dict()
    for entity, file_path in stata_file_by_entity.items():
        assert os.path.exists(file_path), "Invalid file path: {}".format(file_path)
        entity_data_frame = input_data_frame_by_entity[entity] = pd.read_stata(file_path)
        variables_from_stata_files += list(entity_data_frame.columns)
    data['input_data_frame_by_entity_by_period'] = input_data_frame_by_entity_by_period

    return variables_from_stata_files


def load_table(config_files_directory, variables: Optional[List] = None, collection: Optional[str] = None, survey: Optional[str] = None,
        input_data_survey_prefix: Optional[str] = None, data_year = None, table: Optional[str] = None, batch_size=None, batch_index=0, filter_by=None) -> pd.DataFrame:
    """
    Load values from table from a survey in a collection.

    Args:
        config_files_directory : _description_.
        variables (List, optional): List of the variables to retrieve in the table. Defaults to None to get all the variables.
        collection (str, optional): Collection. Defaults to None.
        survey (str, optional): Survey. Defaults to None.
        input_data_survey_prefix (str, optional): Prefix of the survey to be combined with data year. Defaults to None.
        data_year (_type_, optional): Year of the survey data. Defaults to None.
        table (str, optional): Table. Defaults to None.

    Returns:
        pandas.DataFrame: A table with the retrieved variables
    """
    survey_collection = SurveyCollection.load(collection = collection, config_files_directory=config_files_directory)
    if survey is not None:
        survey = survey
    else:
        survey = f"{input_data_survey_prefix}_{data_year}"
    survey_ = survey_collection.get_survey(survey)
    log.debug("Loading table {} in survey {} from collection {}".format(table, survey, collection))
    if batch_size:
        return survey_.get_values(table = table, variables = variables, batch_size = batch_size, batch_index = batch_index, filter_by=filter_by)
    else:
        return survey_.get_values(table = table, variables = variables, filter_by=filter_by)
