"""Tables."""

from chardet.universaldetector import UniversalDetector
import collections
import csv
import datetime
import errno
import gc
import logging
import os
import pandas
from pyarrow import parquet as pq


from openfisca_survey_manager import read_sas

try:
    from openfisca_survey_manager.read_spss import read_spss
except ImportError:
    read_spss = None


log = logging.getLogger(__name__)


reader_by_source_format = dict(
    # Rdata = pandas.rpy.common.load_data,
    csv = pandas.read_csv,
    sas = read_sas.read_sas,
    spss = read_spss,
    stata = pandas.read_stata,
    parquet = pandas.read_parquet,
    )


class Table(object):
    """A table of a survey."""
    label = None
    name = None
    source_format = None
    survey = None
    variables = None
    parquet_file = None

    def __init__(self, survey = None, name = None, label = None, source_format = None, variables = None, parquet_file = None,
                 **kwargs):
        assert name is not None, "A table should have a name"
        self.name = name
        self.label = label
        self.source_format = source_format
        self.variables = variables
        self.parquet_file = parquet_file
        self.informations = kwargs

        from .surveys import Survey  # Keep it here to avoid infinite recursion
        assert isinstance(survey, Survey), f'survey is of type {type(survey)} and not {Survey}'
        self.survey = survey
        if not survey.tables:
            survey.tables = collections.OrderedDict()

        survey.tables[name] = collections.OrderedDict(
            source_format = source_format,
            variables = variables,
            parquet_file = parquet_file,
            )

    def _check_and_log(self, data_file_path, store_file_path):
        """
        Check if the file exists and log the insertion.

        Args:
            data_file_path: Data file path
            store_file_path: Store file or dir path

        Raises:
            Exception: File not found
        """
        assert store_file_path is not None, "Store file path cannot be None"
        if not os.path.isfile(data_file_path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), data_file_path)

        log.info(f"Inserting table {self.name} from file {data_file_path} in store file {store_file_path} at point {self.name}")

    def _is_stored(self):
        if self.survey.hdf5_file_path is not None:
            store = pandas.HDFStore(self.survey.hdf5_file_path)
            if self.name in store:
                log.info(f'Exiting without overwriting {self.name} in {self.survey.hdf5_file_path}')
                store.close()
                return True

            store.close()
            return False
        else:
            return False

    def _save(self, data_frame: pandas.DataFrame = None, store_format = "hdf5"):
        """
        Save a data frame in the store according to is format (HDF5 or Parque).
        """
        assert data_frame is not None
        variables = self.variables

        if variables:
            stored_variables = list(set(variables).intersection(set(data_frame.columns)))
            log.info(f'The folloging variables are stored: {stored_variables}')
            if set(stored_variables) != set(variables):
                log.info(f'variables wanted by the user that were not available: {list(set(variables) - set(stored_variables))}')
            data_frame = data_frame[stored_variables].copy()

        assert store_format in ["hdf5", "parquet"], f"invalid store_format: {store_format}"
        if store_format == "hdf5":
            self.save_data_frame_to_hdf5(data_frame)
        else:
            parquet_file_path = self.survey.parquet_file_path
            log.info(f"Inserting table {self.name} in Parquet file {parquet_file_path}")
            self.save_data_frame_to_parquet(data_frame)
        gc.collect()

    def fill_store(self, data_file, overwrite: bool = False, clean: bool = False, **kwargs):
        """
        Fill the store (HDF5 or parquet file) with the table.
        Read the `data_file` in parameter and save it to the store.

        Args:
            data_file (_type_, optional): The data file path. Defaults to None.
            overwrite (bool, optional): Overwrite the data. Defaults to False.
            clean (bool, optional): Clean the raw data befoe saving. Defaults to False.
            store_format (str, optional): _description_. Defaults to "hdf5".

        Raises:
            e: Skip file if error
        """
        if not overwrite and self._is_stored():
            log.info(
                f'Exiting without overwriting {self.name} in {self.survey.hdf5_file_path}'
                )
            return

        start_table_time = datetime.datetime.now()
        data_frame = self.read_source(data_file, **kwargs)
        try:
            if clean:
                clean_data_frame(data_frame)
            self._save(data_frame = data_frame, store_format = self.survey.store_format)
            log.info(f"File {data_file} has been processed in {datetime.datetime.now() - start_table_time}")
        except Exception as e:
            log.info(f'Skipping file {data_file} because of following error \n {e}')
            raise e

    def read_parquet_columns(self, parquet_file = None) -> list:
        """
        Initialize the table from a parquet file.
        """
        if parquet_file is None:
            parquet_file = self.parquet_file
        log.info(f"Initializing table {self.name} from parquet file {parquet_file}")
        self.source_format = 'parquet'
        parquet_schema = pq.read_schema(parquet_file)
        self.variables = parquet_schema.names
        self.survey.tables[self.name]["variables"] = self.variables
        return self.variables

    def read_source(self, data_file, **kwargs):
        source_format = self.source_format
        store_file_path = (
            self.survey.hdf5_file_path
            if self.survey.store_format == "hdf5"
            else self.survey.parquet_file_path
            )

        self._check_and_log(data_file, store_file_path = store_file_path)
        reader = reader_by_source_format[source_format]
        try:
            if source_format == 'csv':
                try:
                    data_frame = reader(data_file, **kwargs)

                    if len(data_frame.columns) == 1 and ";" in len(data_frame.columns[0]):
                        raise ValueError("A ';' is present in the unique column name. Looks like we got the wrong separator.")

                except Exception:
                    log.debug(f"Failing to read {data_file}, Trying to infer encoding and dialect/separator")

                    # Detect encoding
                    detector = UniversalDetector()
                    with open(data_file, 'rb') as csvfile:
                        for line in csvfile:
                            detector.feed(line)
                            if detector.done:
                                break
                        detector.close()

                    encoding = detector.result['encoding']
                    confidence = detector.result['confidence']

                    # Sniff dialect
                    try:
                        with open(data_file, 'r', newline = "", encoding = encoding) as csvfile:
                            dialect = csv.Sniffer().sniff(csvfile.read(1024), delimiters=";,")
                    except Exception:
                        # Sometimes the sniffer fails, we switch back to the default ... of french statistical data
                        dialect = None
                        delimiter = ";"

                    log.debug(
                        f"dialect.delimiter = {dialect.delimiter if dialect is not None else delimiter}, encoding = {encoding}, confidence = {confidence}"
                        )
                    kwargs['engine'] = "python"
                    if dialect:
                        kwargs['dialect'] = dialect
                    else:
                        kwargs['delimiter'] = delimiter
                    kwargs['encoding'] = encoding
                    data_frame = reader(data_file, **kwargs)

            else:
                data_frame = reader(data_file, **kwargs)

        except Exception as e:
            log.info(f'Error while reading {data_file}')
            raise e

        gc.collect()
        return data_frame

    def save_data_frame_to_hdf5(self, data_frame, **kwargs):
        """Save a data frame in the HDF5 file format."""
        hdf5_file_path = self.survey.hdf5_file_path
        log.info(f"Inserting table {self.name} in HDF file {hdf5_file_path}")
        store_path = self.name
        try:
            data_frame.to_hdf(hdf5_file_path, store_path, append = False, **kwargs)
        except (TypeError, NotImplementedError):
            log.info(f"Type problem(s) when creating {store_path} in {hdf5_file_path}")
            dtypes = data_frame.dtypes
            # Checking for strings
            converted_dtypes = dtypes.isin(['mixed', 'unicode'])
            if converted_dtypes.any():
                log.info(f"The following types are converted to strings \n {dtypes[converted_dtypes]}")
                # Conversion to strings
                for column in dtypes[converted_dtypes].index:
                    data_frame[column] = data_frame[column].copy().astype(str)

            # Checking for remaining categories
            dtypes = data_frame.dtypes
            converted_dtypes = dtypes.isin(['category'])
            if not converted_dtypes.empty:  # With category table format is needed
                log.info(f"The following types are added as category using the table format\n {dtypes[converted_dtypes]}")
                data_frame.to_hdf(hdf5_file_path, store_path, append = False, format = 'table', **kwargs)

        self.variables = list(data_frame.columns)

    def save_data_frame_to_parquet(self, data_frame):
        """Save a data frame in the Parquet file format."""
        parquet_file_path = self.survey.parquet_file_path

        if not os.path.isdir(parquet_file_path):
            log.warn(f"{parquet_file_path} where to store table {self.name} data does not exist: we create the directory")
            os.makedirs(parquet_file_path)
        self.parquet_file = parquet_file_path + "/" + self.name
        data_frame.to_parquet(self.parquet_file)
        self.variables = list(data_frame.columns)

        self.survey.tables[self.name]["parquet_file"] = self.parquet_file
        self.survey.tables[self.name]["variables"] = self.variables


def clean_data_frame(data_frame):
    """Clean a data frame.

    The following steps are executed:
    - drop empty columns
    - replace empty strings with zeros
    - convert string columns to integers
    """
    data_frame.columns = data_frame.columns.str.lower()
    object_column_names = list(data_frame.select_dtypes(include=["object"]).columns)
    log.info(f"The following variables are to be cleaned or left as strings : \n {object_column_names}")
    for column_name in object_column_names:
        if data_frame[column_name].isnull().all():  #
            log.info(f"Drop empty column {column_name}")
            data_frame.drop(column_name, axis = 1, inplace = True)
            continue

        values = [str(value) for value in data_frame[column_name].value_counts().keys()]
        empty_string_present = "" in values
        if empty_string_present:
            values.remove("")
        all_digits = all([value.strip().isdigit() for value in values])
        no_zero = all([value != 0 for value in values])
        if all_digits and no_zero:
            log.info(f"Replacing empty string with zero for variable {column_name}")
            data_frame.replace(
                to_replace = {column_name: {"": 0}},
                inplace = True,
                )
            log.info(f"Converting string variable {column_name} to integer")
            try:
                data_frame[column_name] = data_frame[column_name].astype("int")
            except OverflowError:
                log.info(f'OverflowError when converting {column_name} to int. Keeping as {data_frame[column_name].dtype}')
