import logging

from pandas.core.frame import DataFrame

log = logging.getLogger(__name__)


def read_sas(sas_file_path) -> DataFrame:
    try:
        import pyreadstat  # noqa

        data_frame, _ = pyreadstat.read_sas7bdat(sas_file_path)
    except ImportError as e1:
        log.info("pyreadstat not available trying SAS7BDAT")
        try:
            from sas7bdat import SAS7BDAT  # noqa

            data_frame = SAS7BDAT(sas_file_path).to_data_frame()
        except ImportError:
            log.info("Neither pyreadstat nor SAS7BDAT are available")
            print(e1)  # noqa analysis:ignore
            raise

    return data_frame
