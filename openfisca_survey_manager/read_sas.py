import logging
from pandas.core.frame import DataFrame

log = logging.getLogger(__name__)


def read_sas(sas_file_path, clean = False) -> DataFrame:
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
            print(e1)  # noqa analysis:ignore
            raise(e2)

    return data_frame
