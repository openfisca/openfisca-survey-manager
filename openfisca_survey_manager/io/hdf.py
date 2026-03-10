"""HDF5 write support for survey tables."""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)

# PyTables / pandas-HDF5 require node names to match ^[a-zA-Z_][a-zA-Z0-9_]*$
# to avoid NaturalNameWarning. We normalize table names (e.g. person_2017-01 -> person_2017_01).
_HDF5_SAFE_PATTERN = re.compile(r"[^a-zA-Z0-9_]")


def hdf5_safe_key(name: str) -> str:
    """Return an HDF5 node name safe for PyTables (valid Python identifier)."""
    return _HDF5_SAFE_PATTERN.sub("_", name)


def write_table_to_hdf5(
    data_frame: pd.DataFrame,
    *,
    hdf5_file_path: str,
    store_path: str,
    **kwargs: Any,
) -> None:
    """Write a DataFrame to HDF5.

    Mirrors historical behavior from `tables.Table.save_data_frame_to_hdf5`.
    May mutate `data_frame` (type conversions) to ensure it can be written.
    """
    key = hdf5_safe_key(store_path)
    try:
        data_frame.to_hdf(hdf5_file_path, key=key, append=False, **kwargs)
    except (TypeError, NotImplementedError):
        log.info("Type problem(s) when creating %s in %s", store_path, hdf5_file_path)
        dtypes = data_frame.dtypes
        # Checking for strings
        converted_dtypes = dtypes.isin(["mixed", "unicode"])
        if converted_dtypes.any():
            log.info("The following types are converted to strings %s", dtypes[converted_dtypes])
            for column in dtypes[converted_dtypes].index:
                data_frame[column] = data_frame[column].copy().astype(str)

        # Checking for remaining categories
        dtypes = data_frame.dtypes
        converted_dtypes = dtypes.isin(["category"])
        if not converted_dtypes.empty:  # With category table format is needed
            log.info(
                "The following types are added as category using the table format %s",
                dtypes[converted_dtypes],
            )
            data_frame.to_hdf(hdf5_file_path, key=key, append=False, format="table", **kwargs)
