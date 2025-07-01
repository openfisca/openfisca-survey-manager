import gc
import logging
import os
from configparser import ConfigParser

from pandas import HDFStore

from openfisca_survey_manager.paths import default_config_files_directory

log = logging.getLogger(__name__)


temporary_store_by_file_path = {}


def temporary_store_decorator(
    config_files_directory=default_config_files_directory, file_name=None
):
    parser = ConfigParser()
    config_ini = os.path.join(config_files_directory, "config.ini")
    assert os.path.exists(config_ini), f"{config_ini} is not a valid path"
    read_config_file_name = parser.read([config_ini])
    tmp_directory = parser.get("data", "tmp_directory")
    assert tmp_directory is not None, f"tmp_directory is not set: {tmp_directory!r} in {read_config_file_name}"
    assert os.path.isabs(tmp_directory), (
        f"tmp_directory should be an absolut path: {tmp_directory!r} in {read_config_file_name}"
    )
    if not os.path.isdir(tmp_directory):
        log.info(
            f"tmp_directory does not exist: {tmp_directory!r} in {read_config_file_name}. Creating it."
        )
        os.makedirs(tmp_directory)

    assert file_name is not None
    if not file_name.endswith(".h5"):
        file_name = f"{file_name}.h5"
    file_path = os.path.join(tmp_directory, file_name)

    def actual_decorator(func):
        def func_wrapper(*args, **kwargs):
            just_openned = False
            temporary_store = temporary_store_by_file_path.get(file_path)
            if temporary_store is None:
                temporary_store = HDFStore(file_path)
                temporary_store_by_file_path[file_path] = temporary_store
                just_openned = True

            try:
                return func(*args, temporary_store=temporary_store, **kwargs)
            except Exception:
                raise
            finally:
                gc.collect()
                if just_openned:
                    temporary_store.close()
                    del temporary_store_by_file_path[file_path]

        return func_wrapper

    return actual_decorator


def get_store(config_files_directory=default_config_files_directory, file_name=None):
    parser = ConfigParser()
    config_ini = os.path.join(config_files_directory, "config.ini")
    parser.read(config_ini)
    tmp_directory = parser.get("data", "tmp_directory")
    assert file_name is not None
    if not file_name.endswith(".h5"):
        file_name = f"{file_name}.h5"
    file_path = os.path.join(tmp_directory, file_name)
    return HDFStore(file_path)


def save_hdf_r_readable(
    data_frame,
    config_files_directory=default_config_files_directory,
    file_name=None,
    file_path=None,
):
    if file_path is None:
        parser = ConfigParser()
        config_ini = os.path.join(config_files_directory, "config.ini")
        parser.read(config_ini)
        tmp_directory = parser.get("data", "tmp_directory")
        if file_name is not None:
            if not file_name.endswith(".h5"):
                file_name = f"{file_name}.h5"
            file_path = os.path.join(tmp_directory, file_name)
        else:
            file_path = os.path.join(tmp_directory, "temp.h5")

    store = HDFStore(file_path, "w", complib="zlib", complevel=5)
    store.put("dataframe", data_frame, data_columns=data_frame.columns)
    store.close()
