import logging


log = logging.getLogger(__name__)


def read_sas(sas_file_path, clean = False):
    try:
        import pyreadstat
        data_frame, _ = pyreadstat.read_sas7bdat(sas_file_path)
    except ImportError as e1:
        log.info("pyreadstat not available trying SAS7BDAT")
        try:
            from sas7bdat import SAS7BDAT
            data_frame = SAS7BDAT(sas_file_path).to_data_frame()
        except ImportError as e2:
            log.info("pyreadstat not available trying SAS7BDAT")
            print(e1)
            raise(e2)

    return data_frame
