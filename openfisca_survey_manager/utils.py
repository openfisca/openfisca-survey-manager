# -*- coding: utf-8 -*-


import logging

from openfisca_core import periods
from openfisca_core.parameters import ParameterNode, Scale


log = logging.getLogger(__name__)


def inflate_parameters(parameters, inflator, base_year, last_year = None, ignore_missing_units = False):

    if (last_year is not None) and (last_year > base_year + 1):
            for year in range(base_year + 1, last_year + 1):
                inflate_parameters(parameters, inflator, year - 1, last_year = year, ignore_missing_units = ignore_missing_units)

    else:
        if last_year is None:
            last_year = base_year + 1

        assert last_year == base_year + 1

        for name, sub_parameter in parameters.children.items():
            if isinstance(sub_parameter, ParameterNode):
                inflate_parameters(sub_parameter, inflator, base_year, last_year, ignore_missing_units = ignore_missing_units)
            else:
                if ignore_missing_units:
                    if not hasattr(sub_parameter, 'metadata'):
                        continue
                    if 'unit' not in sub_parameter.metadata:
                        continue

                assert hasattr(sub_parameter, 'metadata'), "{} doesn't have metadata".format(sub_parameter.name)
                unit_types = set(sub_parameter.metadata.keys()).intersection(set([
                    'rate_unit',
                    'threshold_unit',
                    'unit',
                    ]))
                assert unit_types, "No admissible unit in metadata for parameter {}".format(
                    sub_parameter.name)
                if len(unit_types) > 1:
                    assert unit_types == set(['threshold_unit', 'rate_unit']), \
                        "Too much admissible units in metadata for parameter {}".format(
                            sub_parameter.name)
                unit_by_type = dict([
                    (unit_type, sub_parameter.metadata[unit_type]) for unit_type in unit_types
                    ])

                for unit_type, unit in unit_by_type.items():
                    if sub_parameter.metadata[unit_type].startswith("currency"):
                        inflate_parameter_leaf(sub_parameter, base_year, inflator, unit_type = unit_type)


def inflate_parameter_leaf(sub_parameter, base_year, inflator, unit_type = 'unit'):
    """
    Inflate a Parameter leaf according to unit type

    Basic unit type are supposed by default
    Other admissible unit types are threshold_unit and rate_unit
    """

    if isinstance(sub_parameter, Scale):
        if unit_type == 'unit':
            for bracket in sub_parameter.brackets:
                threshold = bracket.children['threshold']
                inflate_parameter_leaf(threshold, base_year, inflator)
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
        restricted_to_base_year_value_list = [
            parameter_at_instant for parameter_at_instant in sub_parameter.values_list
            if periods.instant(parameter_at_instant.instant_str).year == base_year
            ]
        # When value is changed in the base year
        if restricted_to_base_year_value_list:
            for parameter_at_instant in reversed(restricted_to_base_year_value_list):
                if parameter_at_instant.instant_str.startswith(str(base_year)):
                    value = (
                        parameter_at_instant.value * (1 + inflator)
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
                sub_parameter("{}-12-31".format(base_year)) * (1 + inflator)
                if sub_parameter("{}-12-31".format(base_year)) is not None
                else None
                )
            sub_parameter.update(
                start = "{}-01-01".format(base_year + 1),
                value = value
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

    for name, sub_parameter in parameters.children.items():
        if isinstance(sub_parameter, ParameterNode):
            parameters_asof(sub_parameter, instant)
        else:
            if isinstance(sub_parameter, Scale):
                for bracket in sub_parameter.brackets:
                    threshold = bracket.children['threshold']
                    rate = bracket.children['rate']
                    leaf_asof(threshold, instant)
                    leaf_asof(rate, instant)
            else:
                leaf_asof(sub_parameter, instant)


def variables_asof(tax_benefit_system, instant, variables_list = []):
    if isinstance(instant, str):
        instant = periods.instant(instant)
    assert isinstance(instant, periods.Instant)

    if variables_list == []:
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
