# -*- coding: utf-8 -*-


import logging

from openfisca_core import periods
from openfisca_core.parameters import ParameterNode, Scale


log = logging.getLogger(__name__)


def clean_data_frame(data_frame):
    object_column_names = list(data_frame.select_dtypes(include=["object"]).columns)
    log.info(
        "The following variables are to be cleaned or left as strings : \n {}".format(object_column_names)
        )
    for column_name in object_column_names:
        if data_frame[column_name].isnull().all():  #
            log.info("Drop empty column {}".format(column_name))
            data_frame.drop(column_name, axis = 1, inplace = True)
            continue

        values = list(data_frame[column_name].value_counts().keys())
        empty_string_present = "" in values
        if empty_string_present:
            values.remove("")
        all_digits = all([value.strip().isdigit() for value in values])
        no_zero = all([value != 0 for value in values])
        if all_digits and no_zero:
            log.info(
                "Replacing empty string with zero for variable {}".format(column_name)
                )
            data_frame.replace(
                to_replace = {
                    column_name: {"": 0},
                    },
                inplace = True,
                )
            log.info(
                "Converting string variable {} to integer".format(column_name)
                )
            try:
                data_frame[column_name] = data_frame[column_name].astype("int")
            except OverflowError:
                log.info(
                    'OverflowError when converting {} to int. Keeping as {}'.format(
                        column_name, data_frame[column_name].dtype)
                    )


def inflate_parameters(parameters, inflator, base_year, last_year = None, ignore_missing_units = False):

    if (last_year is not None) and (last_year > base_year + 1):
            for year in range(base_year + 1, last_year + 1):
                inflate_parameters(parameters, inflator, year - 1, last_year = year)

    else:
        if last_year is None:
            last_year = base_year + 1

        assert last_year == base_year + 1

        for name, sub_parameter in parameters.children.items():
            if isinstance(sub_parameter, ParameterNode):
                inflate_parameters(sub_parameter, inflator, base_year, last_year)
            else:
                if ignore_missing_units:
                    if not hasattr(sub_parameter, 'metadata'):
                        return
                    if 'unit' not in sub_parameter.metadata:
                        return

                else:
                    assert hasattr(sub_parameter, 'metadata'), "{} doesn't have metadata".format(sub_parameter.name)
                    unit_types = set(sub_parameter.metadata.keys()).intersection(set([
                        'rate_unit',
                        'threshold_unit',
                        'unit',
                        ]))
                    assert len(unit_types) > 0, "No admissible unit in metadata for parameter {}".format(
                        sub_parameter.name)
                    if len(unit_types) > 1:
                        assert unit_types == set(['threshold_unit', 'rate_unit']), \
                            "Too much admissible units in metadata for parameter {}".format(
                                sub_parameter.name)
                    unit_by_name = dict([
                        (name, sub_parameter.metadata[name]) for name in unit_types
                        ])
                    print unit_by_name
                if sub_parameter.metadata['unit'].startswith("currency"):
                    inflate_parameter_leaf(sub_parameter, base_year, inflator)


def inflate_parameter_leaf(sub_parameter, base_year, inflator):

    if isinstance(sub_parameter, Scale):
        for bracket in sub_parameter.brackets:
            threshold = bracket.children['threshold']
            inflate_parameter_leaf(threshold, base_year, inflator)
        return

    # Remove new values for year > base_year
    kept_instants_str = [
        parameter_at_instant.instant_str
        for parameter_at_instant in sub_parameter.values_list
        if periods.instant(parameter_at_instant.instant_str).year <= base_year
        ]
    if len(kept_instants_str) == 0:
        return

    last_admissible_instant_str = max(kept_instants_str)
    sub_parameter.update(
        start = last_admissible_instant_str,
        value = sub_parameter(last_admissible_instant_str)
        )
    for parameter_at_instant in reversed(sub_parameter.values_list):
        # When value is changed in the base year
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
        # Or use the value at that instant even when it is defined earlier tahn the abse year
        else:
            value = (
                sub_parameter("{}-01-01".format(base_year)) * (1 + inflator)
                if sub_parameter("{}-01-01".format(base_year)) is not None
                else None
                )
            sub_parameter.update(
                start = "{}-01-01".format(base_year + 1),
                value = value
                )
