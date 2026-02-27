"""Data frame cleaning (column normalization, empty handling)."""

import logging

import pandas as pd

log = logging.getLogger(__name__)


def clean_data_frame(data_frame: pd.DataFrame) -> None:
    """Clean a data frame in place.

    The following steps are executed:
    - drop empty columns
    - replace empty strings with zeros where appropriate
    - convert string columns to integers when all values are digits
    """
    data_frame.columns = data_frame.columns.str.lower()
    object_column_names = list(data_frame.select_dtypes(include=["object"]).columns)
    log.info("The following variables are to be cleaned or left as strings : %s", object_column_names)
    for column_name in object_column_names:
        if column_name not in data_frame.columns:
            continue
        if data_frame[column_name].isnull().all():
            log.info("Drop empty column %s", column_name)
            data_frame.drop(column_name, axis=1, inplace=True)
            continue

        values = [str(value) for value in data_frame[column_name].value_counts()]
        empty_string_present = "" in values
        if empty_string_present:
            values.remove("")
        all_digits = all(value.strip().isdigit() for value in values)
        no_zero = all(value != "0" for value in values)
        if all_digits and no_zero:
            log.info("Replacing empty string with zero for variable %s", column_name)
            data_frame.replace(
                to_replace={column_name: {"": 0}},
                inplace=True,
            )
            log.info("Converting string variable %s to integer", column_name)
            try:
                data_frame[column_name] = data_frame[column_name].astype("int")
            except (OverflowError, ValueError):
                log.info(
                    "OverflowError when converting %s to int. Keeping as %s",
                    column_name,
                    data_frame[column_name].dtype,
                )
