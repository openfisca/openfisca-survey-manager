"""Table: a table of a survey (core I/O and storage)."""

from __future__ import annotations

import collections
import csv
import datetime
import errno
import gc
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import pandas
from chardet.universaldetector import UniversalDetector
from pyarrow import parquet as pq

from openfisca_survey_manager.exceptions import SurveyIOError
from openfisca_survey_manager.io.readers import read_sas
from openfisca_survey_manager.io.writers import write_table_to_hdf5, write_table_to_parquet
from openfisca_survey_manager.processing.cleaning import clean_data_frame

try:
    from openfisca_survey_manager.io.readers import read_spss
except ImportError:
    read_spss = None  # optional dependency (savReaderWriter)

if TYPE_CHECKING:
    from openfisca_survey_manager.core.survey import Survey

log = logging.getLogger(__name__)

reader_by_source_format = {
    "csv": pandas.read_csv,
    "sas": read_sas,
    "spss": read_spss,
    "stata": pandas.read_stata,
    "parquet": pandas.read_parquet,
}


class Table:
    """A table of a survey."""

    label: Optional[str] = None
    name: Optional[str] = None
    source_format: Optional[str] = None
    survey: Optional[Survey] = None
    variables: Optional[list[str]] = None
    parquet_file: Optional[str] = None

    def __init__(
        self,
        survey: Optional[Survey] = None,
        name: Optional[str] = None,
        label: Optional[str] = None,
        source_format: Optional[str] = None,
        variables: Optional[list[str]] = None,
        parquet_file: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        assert name is not None, "A table should have a name"
        self.name = name
        self.label = label
        self.source_format = source_format
        self.variables = variables
        self.parquet_file = parquet_file
        self.informations = kwargs

        from openfisca_survey_manager.core.survey import Survey

        assert isinstance(survey, Survey), f"survey is of type {type(survey)} and not {Survey}"
        self.survey = survey
        if not survey.tables:
            survey.tables = collections.OrderedDict()

        survey.tables[name] = collections.OrderedDict(
            source_format=source_format,
            variables=variables,
            parquet_file=parquet_file,
        )

    def _check_and_log(self, data_file_path: str, store_file_path: Optional[str]) -> None:
        assert store_file_path is not None, "Store file path cannot be None"
        if not Path(data_file_path).is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), data_file_path)

        log.info(
            f"Inserting table {self.name} from file {data_file_path} in store file {store_file_path} "
            f"at point {self.name}"
        )

    def _is_stored(self) -> bool:
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

    def _save(
        self,
        data_frame: Optional[pandas.DataFrame] = None,
        store_format: str = "hdf5",
    ) -> None:
        assert data_frame is not None
        variables = self.variables

        if variables:
            stored_variables = list(set(variables).intersection(set(data_frame.columns)))
            log.info("The following variables are stored: %s", stored_variables)
            if set(stored_variables) != set(variables):
                log.info(
                    "variables wanted by the user that were not available: "
                    f"{list(set(variables) - set(stored_variables))}"
                )
            data_frame = data_frame[stored_variables].copy()

        assert store_format in ["hdf5", "parquet"], f"invalid store_format: {store_format}"
        if store_format == "hdf5":
            log.warning(
                "HDF5 will no longer be the default format in a future version. Please use parquet format instead."
            )
            self.save_data_frame_to_hdf5(data_frame)
        else:
            parquet_file_path = self.survey.parquet_file_path
            log.info(f"Inserting table {self.name} in Parquet file {parquet_file_path}")
            self.save_data_frame_to_parquet(data_frame)
        gc.collect()

    def fill_store(
        self,
        data_file: str,
        overwrite: bool = False,
        clean: bool = False,
        **kwargs: Any,
    ) -> None:
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

    def read_parquet_columns(self, parquet_file: Optional[str] = None) -> list[str]:
        if parquet_file is None:
            parquet_file = self.parquet_file
        log.info(f"Initializing table {self.name} from parquet file {parquet_file}")
        self.source_format = "parquet"
        parquet_schema = pq.read_schema(parquet_file)
        self.variables = parquet_schema.names
        self.survey.tables[self.name]["variables"] = self.variables
        return self.variables

    def _read_csv_with_inferred_encoding(
        self, data_file: str, reader: Any, kwargs: dict[str, Any]
    ) -> pandas.DataFrame:
        """Read CSV, inferring encoding and dialect if default read fails."""
        log.debug("Failing to read %s, trying to infer encoding and dialect/separator", data_file)
        detector = UniversalDetector()
        with Path(data_file).open("rb") as csvfile:
            for line in csvfile:
                detector.feed(line)
                if detector.done:
                    break
        detector.close()
        encoding = detector.result["encoding"]
        confidence = detector.result["confidence"]
        try:
            with Path(data_file).open("r", newline="", encoding=encoding) as csvfile:
                dialect = csv.Sniffer().sniff(csvfile.read(1024), delimiters=";,")
        except Exception:
            dialect = None
            delimiter = ";"
        log.debug(
            "dialect.delimiter = %s, encoding = %s, confidence = %s",
            dialect.delimiter if dialect is not None else delimiter,
            encoding,
            confidence,
        )
        kwargs = {**kwargs, "engine": "python", "encoding": encoding}
        if dialect:
            kwargs["dialect"] = dialect
        else:
            kwargs["delimiter"] = delimiter
        return reader(data_file, **kwargs)

    def _apply_stata_categorical_strategy(
        self,
        data_frame: pandas.DataFrame,
        data_file: str,
        categorical_strategy: str,
    ) -> None:
        """Apply categorical_strategy (unique_labels, codes, skip) to Stata value labels in place."""
        from pandas.io.stata import StataReader

        stata_reader = StataReader(data_file)
        value_labels = stata_reader.value_labels()
        for col_name, labels in value_labels.items():
            if col_name not in data_frame.columns:
                continue
            if categorical_strategy == "unique_labels":
                unique_labels = {}
                seen_labels = {}
                for code, label in labels.items():
                    if pandas.isna(code):
                        unique_labels[code] = label
                    elif label in seen_labels:
                        unique_labels[code] = f"{label} ({code})"
                    else:
                        unique_labels[code] = label
                        seen_labels[label] = code
                code_to_label = {code: unique_labels[code] for code in sorted(labels.keys())}
                data_frame[col_name] = data_frame[col_name].map(code_to_label)
                data_frame[col_name] = pandas.Categorical(
                    data_frame[col_name],
                    categories=list(code_to_label.values()),
                    ordered=False,
                )
            elif categorical_strategy == "codes":
                codes = sorted([c for c in labels if pandas.notna(c)])
                if codes:
                    data_frame[col_name] = pandas.Categorical(data_frame[col_name], categories=codes, ordered=False)
            elif categorical_strategy != "skip":
                log.warning("Unknown categorical_strategy %r, using 'skip'", categorical_strategy)

    def read_source(self, data_file: str, **kwargs: Any) -> pandas.DataFrame:
        source_format = self.source_format
        store_file_path = (
            self.survey.hdf5_file_path if self.survey.store_format == "hdf5" else self.survey.parquet_file_path
        )
        self._check_and_log(data_file, store_file_path=store_file_path)
        reader = reader_by_source_format[source_format]
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
                    data_frame = self._read_csv_with_inferred_encoding(data_file, reader, kwargs)
            elif source_format == "stata":
                if "encoding" in kwargs:
                    kwargs.pop("encoding")
                try:
                    data_frame = reader(data_file, **kwargs)
                except ValueError as e:
                    if "not unique" not in str(e) and "Categorical categories must be unique" not in str(e):
                        raise
                    log.info(
                        "Non-unique value labels detected in %s, using strategy %r",
                        data_file,
                        categorical_strategy,
                    )
                    kwargs_no_cat = {**kwargs, "convert_categoricals": False}
                    data_frame = reader(data_file, **kwargs_no_cat)
                    self._apply_stata_categorical_strategy(data_frame, data_file, categorical_strategy)
            else:
                data_frame = reader(data_file, **kwargs)
        except Exception as e:
            log.info("Error while reading %s", data_file)
            raise e
        gc.collect()
        return data_frame

    def save_data_frame_to_hdf5(self, data_frame: pandas.DataFrame, **kwargs: Any) -> None:
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

    def save_data_frame_to_parquet(self, data_frame: pandas.DataFrame) -> None:
        parquet_file_path = self.survey.parquet_file_path
        self.parquet_file = write_table_to_parquet(
            data_frame,
            parquet_dir_path=parquet_file_path,
            table_name=self.name,
        )
        self.variables = list(data_frame.columns)

        self.survey.tables[self.name]["parquet_file"] = self.parquet_file
        self.survey.tables[self.name]["variables"] = self.variables
