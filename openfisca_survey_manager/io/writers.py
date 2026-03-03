"""Writers for survey data (HDF5, Parquet)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from openfisca_survey_manager.io.hdf import write_table_to_hdf5

log = logging.getLogger(__name__)

__all__ = ["write_table_to_hdf5", "write_table_to_parquet"]


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
