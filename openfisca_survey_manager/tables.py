"""Tables."""

import collections
import csv
import datetime
import errno
import gc
import logging
import os
from pathlib import Path

import pandas
from chardet.universaldetector import UniversalDetector
from pyarrow import parquet as pq

from openfisca_survey_manager import read_sas
from openfisca_survey_manager.exceptions import SurveyIOError
from openfisca_survey_manager.io.writers import write_table_to_hdf5, write_table_to_parquet
from openfisca_survey_manager.processing.cleaning import clean_data_frame

try:
    from openfisca_survey_manager.read_spss import read_spss
except ImportError:
    read_spss = None


log = logging.getLogger(__name__)


reader_by_source_format = {
    # Rdata = pandas.rpy.common.load_data,
    "csv": pandas.read_csv,
    "sas": read_sas.read_sas,
    "spss": read_spss,
    "stata": pandas.read_stata,
    "parquet": pandas.read_parquet,
}


class Table:
    """A table of a survey."""

    label = None
    name = None
    source_format = None
    survey = None
    variables = None
    parquet_file = None

    def __init__(
        self, survey=None, name=None, label=None, source_format=None, variables=None, parquet_file=None, **kwargs
    ):
        assert name is not None, "A table should have a name"
        self.name = name
        self.label = label
        self.source_format = source_format
        self.variables = variables
        self.parquet_file = parquet_file
        self.informations = kwargs

        from .surveys import Survey  # Keep it here to avoid infinite recursion

        assert isinstance(survey, Survey), f"survey is of type {type(survey)} and not {Survey}"
        self.survey = survey
        if not survey.tables:
            survey.tables = collections.OrderedDict()

        survey.tables[name] = collections.OrderedDict(
            source_format=source_format,
            variables=variables,
            parquet_file=parquet_file,
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
        if not Path(data_file_path).is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), data_file_path)

        log.info(
            f"Inserting table {self.name} from file {data_file_path} in store file {store_file_path} "
            f"at point {self.name}"
        )

    def _is_stored(self):
        if self.survey.hdf5_file_path is not None:
            store = pandas.HDFStore(self.survey.hdf5_file_path)
            if self.name in store:
                log.info(f"Exiting without overwriting {self.name} in {self.survey.hdf5_file_path}")
                store.close()
                return True

            store.close()
            return False
        else:
            return False

    def _save(self, data_frame: pandas.DataFrame = None, store_format="hdf5"):
        """
        Save a data frame in the store according to is format (HDF5 or Parque).
        """
        assert data_frame is not None
        variables = self.variables

        if variables:
            stored_variables = list(set(variables).intersection(set(data_frame.columns)))
            log.info(f"The folloging variables are stored: {stored_variables}")
            if set(stored_variables) != set(variables):
                log.info(
                    "variables wanted by the user that were not available: "
                    f"{list(set(variables) - set(stored_variables))}"
                )
            data_frame = data_frame[stored_variables].copy()

        assert store_format in ["hdf5", "parquet"], f"invalid store_format: {store_format}"
        if store_format == "hdf5":
            import warnings

            warnings.warn(
                "HDF5 will no longer be the default format in a future version. Please use parquet format instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            log.warning(
                "HDF5 will no longer be the default format in a future version. Please use parquet format instead."
            )
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
            log.info(f"Exiting without overwriting {self.name} in {self.survey.hdf5_file_path}")
            return

        start_table_time = datetime.datetime.now()
        if self.source_format in ["sas", "parquet"] and "encoding" in kwargs:
            del kwargs["encoding"]
        data_frame = self.read_source(data_file, **kwargs)
        try:
            if clean:
                clean_data_frame(data_frame)
            self._save(data_frame=data_frame, store_format=self.survey.store_format)
            log.info(f"File {data_file} has been processed in {datetime.datetime.now() - start_table_time}")
        except Exception as e:
            log.info(f"Skipping file {data_file} because of following error \n {e}")
            raise e

    def read_parquet_columns(self, parquet_file=None) -> list:
        """
        Initialize the table from a parquet file.
        """
        if parquet_file is None:
            parquet_file = self.parquet_file
        log.info(f"Initializing table {self.name} from parquet file {parquet_file}")
        self.source_format = "parquet"
        parquet_schema = pq.read_schema(parquet_file)
        self.variables = parquet_schema.names
        self.survey.tables[self.name]["variables"] = self.variables
        return self.variables

    def read_source(self, data_file, **kwargs):
        source_format = self.source_format
        store_file_path = (
            self.survey.hdf5_file_path if self.survey.store_format == "hdf5" else self.survey.parquet_file_path
        )

        self._check_and_log(data_file, store_file_path=store_file_path)
        reader = reader_by_source_format[source_format]
        # Extract categorical_strategy early - only stata format uses it
        # Other formats (parquet, csv, etc.) don't support it and will error if passed
        categorical_strategy = (
            kwargs.pop("categorical_strategy", "unique_labels")
            if source_format == "stata"
            else kwargs.pop("categorical_strategy", None)
        )
        try:
            if source_format == "csv":
                try:
                    data_frame = reader(data_file, **kwargs)

                    if len(data_frame.columns) == 1 and ";" in data_frame.columns[0]:
                        raise SurveyIOError(
                            "A ';' is present in the unique column name. Looks like we got the wrong separator."
                        )

                except Exception:
                    log.debug(f"Failing to read {data_file}, Trying to infer encoding and dialect/separator")

                    # Detect encoding
                    detector = UniversalDetector()
                    with Path(data_file).open("rb") as csvfile:
                        for line in csvfile:
                            detector.feed(line)
                            if detector.done:
                                break
                        detector.close()

                    encoding = detector.result["encoding"]
                    confidence = detector.result["confidence"]

                    # Sniff dialect
                    try:
                        with Path(data_file).open("r", newline="", encoding=encoding) as csvfile:
                            dialect = csv.Sniffer().sniff(csvfile.read(1024), delimiters=";,")
                    except Exception:
                        # Sometimes the sniffer fails, we switch back to the default ... of french statistical data
                        dialect = None
                        delimiter = ";"

                    log.debug(
                        f"dialect.delimiter = {dialect.delimiter if dialect is not None else delimiter}, "
                        f"encoding = {encoding}, confidence = {confidence}"
                    )
                    kwargs["engine"] = "python"
                    if dialect:
                        kwargs["dialect"] = dialect
                    else:
                        kwargs["delimiter"] = delimiter
                    kwargs["encoding"] = encoding
                    data_frame = reader(data_file, **kwargs)

            else:
                # Remove encoding parameter for pandas 2.0+ compatibility (not supported in read_stata)
                if "encoding" in kwargs and source_format == "stata":
                    kwargs.pop("encoding")
                # Try to read with categoricals, handle non-unique labels with configurable strategy
                if source_format == "stata":
                    # categorical_strategy already extracted above

                    try:
                        # Try reading with default convert_categoricals (True) if not specified
                        if "convert_categoricals" not in kwargs:
                            data_frame = reader(data_file, **kwargs)
                        else:
                            data_frame = reader(data_file, **kwargs)
                    except ValueError as e:
                        if "not unique" in str(e) or "Categorical categories must be unique" in str(e):
                            log.info(
                                f"Non-unique value labels detected in {data_file}, "
                                f"using strategy '{categorical_strategy}'"
                            )

                            # Read without categoricals first
                            kwargs_no_cat = kwargs.copy()
                            kwargs_no_cat["convert_categoricals"] = False
                            data_frame = reader(data_file, **kwargs_no_cat)

                            # Apply categorical strategy
                            if categorical_strategy == "unique_labels":
                                # Solution 2: Make labels unique by adding code suffix
                                from pandas.io.stata import StataReader

                                stata_reader = StataReader(data_file)
                                value_labels = stata_reader.value_labels()

                                for col_name, labels in value_labels.items():
                                    if col_name in data_frame.columns:
                                        unique_labels = {}
                                        seen_labels = {}

                                        for code, label in labels.items():
                                            if pandas.isna(code):
                                                unique_labels[code] = label
                                            elif label in seen_labels:
                                                # Duplicate label: add code as suffix
                                                unique_labels[code] = f"{label} ({code})"
                                            else:
                                                unique_labels[code] = label
                                                seen_labels[label] = code

                                        # Create mapping code -> unique label
                                        code_to_label = {code: unique_labels[code] for code in sorted(labels.keys())}

                                        # Map codes to unique labels and create categories
                                        data_frame[col_name] = data_frame[col_name].map(code_to_label)
                                        data_frame[col_name] = pandas.Categorical(
                                            data_frame[col_name],
                                            categories=list(code_to_label.values()),
                                            ordered=False,
                                        )

                            elif categorical_strategy == "codes":
                                # Solution 1: Use codes as categories
                                from pandas.io.stata import StataReader

                                stata_reader = StataReader(data_file)
                                value_labels = stata_reader.value_labels()

                                for col_name, labels in value_labels.items():
                                    if col_name in data_frame.columns:
                                        codes = sorted([c for c in labels if pandas.notna(c)])
                                        if codes:
                                            data_frame[col_name] = pandas.Categorical(
                                                data_frame[col_name], categories=codes, ordered=False
                                            )

                            elif categorical_strategy == "skip":
                                # Keep as-is (no categories)
                                pass
                            else:
                                log.warning(f"Unknown categorical_strategy '{categorical_strategy}', using 'skip'")
                        else:
                            raise
                else:
                    data_frame = reader(data_file, **kwargs)

        except Exception as e:
            log.info(f"Error while reading {data_file}")
            raise e

        gc.collect()
        return data_frame

    def save_data_frame_to_hdf5(self, data_frame, **kwargs):
        """Save a data frame in the HDF5 file format."""
        hdf5_file_path = self.survey.hdf5_file_path
        log.info(f"Inserting table {self.name} in HDF file {hdf5_file_path}")
        store_path = self.name
        write_table_to_hdf5(
            data_frame,
            hdf5_file_path=hdf5_file_path,
            store_path=store_path,
            **kwargs,
        )

        self.variables = list(data_frame.columns)

    def save_data_frame_to_parquet(self, data_frame):
        """Save a data frame in the Parquet file format."""
        parquet_file_path = self.survey.parquet_file_path
        self.parquet_file = write_table_to_parquet(
            data_frame,
            parquet_dir_path=parquet_file_path,
            table_name=self.name,
        )
        self.variables = list(data_frame.columns)

        self.survey.tables[self.name]["parquet_file"] = self.parquet_file
        self.survey.tables[self.name]["variables"] = self.variables
