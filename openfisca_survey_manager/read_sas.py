import logging


log = logging.getLogger(__name__)


def read_sas(sas_file_path, clean = False):
    from sas7bdat import SAS7BDAT
    data_frame = SAS7BDAT(sas_file_path).to_data_frame()
    return data_frame
