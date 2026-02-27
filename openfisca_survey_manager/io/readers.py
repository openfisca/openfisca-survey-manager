"""Readers for survey data (SAS, SPSS, DBF, etc.)."""

import logging
from typing import Optional

import pandas as pd
from pandas import DataFrame

log = logging.getLogger(__name__)


def read_sas(sas_file_path: str, clean: bool = False) -> DataFrame:
    """Read a SAS 7BDAT file into a pandas DataFrame."""
    try:
        import pyreadstat

        data_frame, _ = pyreadstat.read_sas7bdat(sas_file_path)
    except ImportError as e1:
        log.info("pyreadstat not available trying SAS7BDAT")
        try:
            from sas7bdat import SAS7BDAT

            data_frame = SAS7BDAT(sas_file_path).to_data_frame()
        except ImportError as e2:
            log.info("Neither pyreadstat nor SAS7BDAT are available")
            log.debug("%s", e1)
            raise e2 from e1

    return data_frame


def read_spss(spss_file_path: str) -> DataFrame:
    """Read an SPSS file into a pandas DataFrame."""
    from savReaderWriter import SavReader

    with SavReader(spss_file_path, returnHeader=True) as reader:
        for record in reader:
            log.debug("%s", record)

    data_frame = DataFrame(list(SavReader(spss_file_path)))
    log.debug("SPSS data frame info: %s", data_frame.info())
    return data_frame


def read_dbf(
    dbf_path: str,
    index: Optional[str] = None,
    cols: Optional[list] = None,
    incl_index: bool = False,
) -> DataFrame:
    """
    Read a DBF file as a pandas DataFrame.

    Arguments
    ---------
    dbf_path : str
        Path to the DBF file to be read
    index : str, optional
        Name of the column to be used as the index of the DataFrame
    cols : list, optional
        List with the names of the columns to be read. Defaults to False (read whole file)
    incl_index : bool
        If True, index is included in the DataFrame as a column too. Defaults to False

    Returns
    -------
    pandas.DataFrame
    """
    try:
        import pysal as ps
    except ModuleNotFoundError as e:
        raise e from None

    db = ps.open(dbf_path)
    if cols:
        if incl_index and index is not None:
            cols.append(index)
        vars_to_read = cols
    else:
        vars_to_read = db.header
    data = {var: db.by_col(var) for var in vars_to_read}
    if index:
        index_col = db.by_col(index)
        db.close()
        return pd.DataFrame(data, index=index_col)
    db.close()
    return pd.DataFrame(data)
