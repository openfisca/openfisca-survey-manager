"""Column harmonization for survey data (lowercase, ident renaming)."""

from __future__ import annotations

import logging
import re

import pandas as pd

log = logging.getLogger(__name__)

# Column names matching this pattern (e.g. ident01, ident2019) are renamed to "ident"
IDENT_COLUMN_PATTERN = re.compile(r"ident\d{2,4}$", re.IGNORECASE)


def harmonize_data_frame_columns(
    data_frame: pd.DataFrame,
    *,
    lowercase: bool = False,
    rename_ident: bool = True,
) -> None:
    """Harmonize column names in place.

    - If lowercase: rename all columns to lowercase.
    - If rename_ident: rename the first column matching ident pattern (e.g. ident01, ident2019) to "ident".
    """
    if lowercase:
        columns = {col: col.lower() for col in data_frame.columns}
        data_frame.rename(columns=columns, inplace=True)

    if rename_ident:
        for column_name in data_frame.columns:
            if IDENT_COLUMN_PATTERN.match(str(column_name)) is not None:
                data_frame.rename(columns={column_name: "ident"}, inplace=True)
                log.info("%s column have been replaced by ident", column_name)
                break
