"""Writers for survey data (HDF5, Parquet)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)


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
    try:
        data_frame.to_hdf(hdf5_file_path, store_path, append=False, **kwargs)
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
            data_frame.to_hdf(hdf5_file_path, store_path, append=False, format="table", **kwargs)


def write_table_to_parquet(
    data_frame: pd.DataFrame,
    *,
    parquet_dir_path: str,
    table_name: str,
) -> str:
    """Write a DataFrame to a parquet file in a directory.

    Mirrors historical behavior from `tables.Table.save_data_frame_to_parquet`.
    May mutate `data_frame` (object -> string) to avoid ArrowTypeError.

    Returns the parquet file path used.
    """
    parquet_dir = Path(parquet_dir_path)
    if not parquet_dir.is_dir():
        log.warning(
            "%s where to store table %s data does not exist: we create the directory",
            parquet_dir_path,
            table_name,
        )
        parquet_dir.mkdir(parents=True)

    parquet_file = str(parquet_dir / f"{table_name}.parquet")

    # Convert object columns with mixed types to string to avoid pyarrow errors
    for col in data_frame.columns:
        if data_frame[col].dtype == "object":
            try:
                data_frame[col] = data_frame[col].astype(str)
            except Exception:
                data_frame[col] = data_frame[col].apply(lambda x: str(x) if pd.notna(x) else None)

    data_frame.to_parquet(parquet_file)
    return parquet_file
