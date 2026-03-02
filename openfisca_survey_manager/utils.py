"""Utilities: re-exports from common.misc + load_table (survey-dependent)."""

import logging
from typing import Optional

import pandas as pd

from openfisca_survey_manager.common.misc import (
    asof,
    do_nothing,
    inflate_parameter_leaf,
    inflate_parameters,
    parameters_asof,
    variables_asof,
)
from openfisca_survey_manager.survey_collections import SurveyCollection

log = logging.getLogger(__name__)

__all__ = [
    "asof",
    "do_nothing",
    "inflate_parameter_leaf",
    "inflate_parameters",
    "load_table",
    "parameters_asof",
    "variables_asof",
]


def load_table(
    config_files_directory,
    variables: Optional[list] = None,
    collection: Optional[str] = None,
    survey: Optional[str] = None,
    input_data_survey_prefix: Optional[str] = None,
    data_year=None,
    table: Optional[str] = None,
    batch_size=None,
    batch_index=0,
    filter_by=None,
) -> pd.DataFrame:
    """
    Load values from table from a survey in a collection.

    Args:
        config_files_directory : _description_.
        variables (List, optional): List of the variables to retrieve in the table.
            Defaults to None to get all the variables.
        collection (str, optional): Collection. Defaults to None.
        survey (str, optional): Survey. Defaults to None.
        input_data_survey_prefix (str, optional): Prefix of the survey to be combined with data year. Defaults to None.
        data_year (_type_, optional): Year of the survey data. Defaults to None.
        table (str, optional): Table. Defaults to None.

    Returns:
        pandas.DataFrame: A table with the retrieved variables
    """
    survey_collection = SurveyCollection.load(collection=collection, config_files_directory=config_files_directory)
    survey = survey if survey is not None else f"{input_data_survey_prefix}_{data_year}"
    survey_ = survey_collection.get_survey(survey)
    log.debug(f"Loading table {table} in survey {survey} from collection {collection}")
    if batch_size:
        return survey_.get_values(
            table=table, variables=variables, batch_size=batch_size, batch_index=batch_index, filter_by=filter_by
        )
    else:
        return survey_.get_values(table=table, variables=variables, filter_by=filter_by)
