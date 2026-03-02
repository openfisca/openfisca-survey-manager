"""Survey: describes survey data and tables."""

from __future__ import annotations

import collections
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union

import pandas
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from openfisca_survey_manager.core.table import Table
from openfisca_survey_manager.exceptions import SurveyIOError, SurveyManagerError
from openfisca_survey_manager.io.hdf import hdf5_safe_key
from openfisca_survey_manager.processing.harmonization import harmonize_data_frame_columns

if TYPE_CHECKING:
    from openfisca_survey_manager.core.dataset import SurveyCollection

log = logging.getLogger(__name__)

source_format_by_extension = {
    "csv": "csv",
    "sas7bdat": "sas",
    "dta": "stata",
    "Rdata": "Rdata",
    "spss": "sav",
    "parquet": "parquet",
}

admissible_source_formats = list(source_format_by_extension.values())


class NoMoreDataError(Exception):
    """Raised when the user asks for more data than available in file."""

    pass


class Survey:
    """An object to describe survey data."""

    hdf5_file_path: Optional[str] = None
    parquet_file_path: Optional[str] = None
    label: Optional[str] = None
    name: Optional[str] = None
    survey_collection: Optional[SurveyCollection] = None
    store_format: Optional[str] = None

    def __init__(
        self,
        name: Optional[str] = None,
        label: Optional[str] = None,
        hdf5_file_path: Optional[str] = None,
        parquet_file_path: Optional[str] = None,
        survey_collection: Optional[SurveyCollection] = None,
        **kwargs: Any,
    ) -> None:
        assert name is not None, "A survey should have a name"
        self.name = name
        self.tables = collections.OrderedDict()
        self.informations = {}
        self.tables_index = {}

        if label is not None:
            self.label = label

        if hdf5_file_path is not None:
            self.hdf5_file_path = hdf5_file_path

        if parquet_file_path is not None:
            self.parquet_file_path = parquet_file_path

        if survey_collection is not None:
            self.survey_collection = survey_collection

        self.informations = kwargs

    def __repr__(self) -> str:
        header = f"""{self.name} : survey data {self.label}
Contains the following tables : \n"""
        tables = yaml.safe_dump(list(self.tables.keys()), default_flow_style=False)
        informations = yaml.safe_dump(self.informations, default_flow_style=False)
        return header + tables + informations

    @classmethod
    def create_from_json(cls, survey_json: dict) -> Survey:
        self = cls(
            name=survey_json.get("name"),
            label=survey_json.get("label"),
            hdf5_file_path=survey_json.get("hdf5_file_path"),
            parquet_file_path=survey_json.get("parquet_file_path"),
            **survey_json.get("informations", {}),
        )
        self.tables = survey_json.get("tables")
        return self

    def dump(self) -> None:
        assert self.survey_collection is not None
        self.survey_collection.dump()

    def fill_store(
        self,
        source_format: Optional[str] = None,
        tables: Optional[List[str]] = None,
        overwrite: Union[bool, List[str]] = True,
        keep_original_parquet_file: bool = False,
        encoding: Optional[str] = None,
        store_format: str = "hdf5",
        categorical_strategy: str = "unique_labels",
    ) -> None:
        assert self.survey_collection is not None
        assert isinstance(overwrite, (bool, list))
        survey = self
        config = survey.survey_collection.config
        directory_path = config.get("data", "output_directory")
        if not Path(directory_path).is_dir():
            log.warning(
                f"{directory_path} who should be the store data directory does not exist: we create the directory"
            )
            Path(directory_path).mkdir(parents=True)

        if source_format == "parquet":
            store_format = "parquet"

        if store_format == "hdf5" and survey.hdf5_file_path is None:
            survey.hdf5_file_path = str(Path(directory_path) / (survey.name + ".h5"))

        if store_format == "parquet" and survey.parquet_file_path is None:
            survey.parquet_file_path = str(Path(directory_path) / survey.name)

        self.store_format = store_format

        if source_format is not None:
            assert source_format in admissible_source_formats, f"Data source format {source_format} is unknown"
            source_formats = [source_format]
        else:
            source_formats = admissible_source_formats

        for source_format in source_formats:
            files = f"{source_format}_files"
            for data_file in survey.informations.get(files, []):
                name = Path(data_file).stem
                extension = Path(data_file).suffix
                if tables is None or name in tables:
                    if keep_original_parquet_file:
                        if re.match(r".*-\d$", name):
                            name = name.split("-")[0]
                            parquet_file = str(Path(data_file).parent)
                            survey.parquet_file_path = str(Path(data_file).parent.parent)
                        else:
                            parquet_file = data_file
                            survey.parquet_file_path = str(Path(data_file).parent)
                        table = Table(
                            label=name,
                            name=name,
                            source_format=source_format_by_extension[extension[1:]],
                            survey=survey,
                            parquet_file=parquet_file,
                        )
                        table.read_parquet_columns(data_file)

                    else:
                        table = Table(
                            label=name,
                            name=name,
                            source_format=source_format_by_extension[extension[1:]],
                            survey=survey,
                        )
                        table.fill_store(
                            data_file,
                            clean=True,
                            overwrite=overwrite if isinstance(overwrite, bool) else table.name in overwrite,
                            encoding=encoding,
                            categorical_strategy=categorical_strategy,
                        )
        self.dump()

    def get_value(
        self,
        variable: str,
        table: Optional[str] = None,
        lowercase: bool = False,
        ignorecase: bool = False,
    ) -> pandas.DataFrame:
        return self.get_values([variable], table)

    def _get_values_from_hdf5(self, table: str, ignorecase: bool = False) -> tuple[pandas.DataFrame, str]:
        """Read table from HDF5 store. Returns (df, resolved_table_name)."""
        assert Path(self.hdf5_file_path).exists(), (
            f"{self.hdf5_file_path} is not a valid path. This could happen because "
            "your data were not builded yet. Please consider using a rebuild option in your code."
        )
        store = pandas.HDFStore(self.hdf5_file_path, "r")
        try:
            # Use same key normalization as at write time (PyTables NaturalNameWarning)
            hdf5_key = hdf5_safe_key(table)
            if ignorecase:
                keys = store.keys()
                eligible_tables = [k for k in keys if hdf5_safe_key(k.lstrip("/")).lower() == hdf5_key.lower()]
                if len(eligible_tables) > 1:
                    raise SurveyManagerError(
                        f"{table} is ambiguous since the following tables are available: {eligible_tables}"
                    )
                if len(eligible_tables) == 0:
                    raise SurveyIOError(f"No eligible available table in {keys}")
                hdf5_key = eligible_tables[0].lstrip("/")
            try:
                df = store.select(hdf5_key)
            except KeyError:
                # Backward compat: try raw table name (old files may have keys with hyphens)
                df = store.select(table)
            return df, table
        except KeyError:
            log.error("No table %s in the file %s", table, self.hdf5_file_path)
            log.error(
                "This could happen because your data were not builded yet. Available tables are: %s",
                store.keys(),
            )
            raise
        finally:
            store.close()

    def _get_values_from_parquet(
        self,
        table: str,
        variables: Optional[List[str]],
        filter_by: Optional[List[tuple]],
        batch_size: Optional[int],
        batch_index: int,
    ) -> pandas.DataFrame:
        """Read table from parquet. Resolves variables from table content if None."""
        if table is None:
            raise SurveyIOError("A table name is needed to retrieve data from a parquet file")
        for table_name, table_content in self.tables.items():
            if table != table_name:
                continue
            parquet_file = table_content.get("parquet_file")
            if Path(parquet_file).is_dir():
                for file in Path(parquet_file).iterdir():
                    if file.suffix == ".parquet":
                        one_parquet_file = str(Path(parquet_file) / file)
                        break
                else:
                    raise SurveyIOError(f"No parquet file found in {parquet_file}")
            else:
                one_parquet_file = parquet_file
            parquet_schema = pq.read_schema(one_parquet_file)
            assert len(parquet_schema.names) >= 1, f"The parquet file {table_content.get('parquet_file')} is empty"
            if variables is None:
                variables = table_content.get("variables")
            if filter_by:
                return pq.ParquetDataset(parquet_file, filters=filter_by).read(columns=variables).to_pandas()
            if batch_size is not None:
                paths = (
                    [str(p) for p in Path(parquet_file).glob("*.parquet")]
                    if Path(parquet_file).is_dir()
                    else [parquet_file]
                )
                tables_list = [pq.read_table(fp, columns=variables) for fp in paths]
                final_table = pa.concat_tables(tables_list) if len(tables_list) > 1 else tables_list[0]
                record_batches = final_table.to_batches(max_chunksize=batch_size)
                if len(record_batches) <= batch_index:
                    raise NoMoreDataError(
                        f"Batch {batch_index} not found in {table_name}. Max index is {len(record_batches)}"
                    )
                return record_batches[batch_index].to_pandas()
            return pq.ParquetDataset(parquet_file).read(columns=variables).to_pandas()
        raise SurveyIOError(f"No table {table} found in {self.parquet_file_path}")

    def get_values(
        self,
        variables: Optional[List[str]] = None,
        table: Optional[str] = None,
        lowercase: bool = False,
        ignorecase: bool = False,
        rename_ident: bool = True,
        batch_size: Optional[int] = None,
        batch_index: int = 0,
        filter_by: Optional[List[tuple]] = None,
    ) -> pandas.DataFrame:
        if self.parquet_file_path is None and self.hdf5_file_path is None:
            raise SurveyIOError(f"No data file found for survey {self.name}")
        if self.hdf5_file_path is not None:
            df, _ = self._get_values_from_hdf5(table or "", ignorecase=ignorecase)
        else:
            df = self._get_values_from_parquet(table, variables, filter_by, batch_size, batch_index)
        harmonize_data_frame_columns(df, lowercase=lowercase, rename_ident=rename_ident)
        if variables is None:
            return df
        diff = set(variables) - set(df.columns)
        if diff:
            raise SurveyIOError(f"The following variable(s) {diff} are missing")
        variables = list(set(variables).intersection(df.columns))
        return df[variables]

    def insert_table(
        self,
        label: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        parquet_file = kwargs.pop("parquet_file", None)
        data_frame = kwargs.pop("data_frame", None)
        if data_frame is None:
            data_frame = kwargs.pop("dataframe", None)

        if data_frame is not None:
            assert isinstance(data_frame, pandas.DataFrame)
            variables = kwargs.pop("variables", None)
            if variables is not None:
                assert set(variables) < set(data_frame.columns)
            else:
                variables = list(data_frame.columns)
            if label is None:
                label = name
            table = Table(label=label, name=name, survey=self, variables=variables, parquet_file=parquet_file)
            assert (table.survey.hdf5_file_path is not None) or (table.survey.parquet_file_path is not None)
            if parquet_file is not None:
                log.debug(f"Saving table {name} in {table.survey.parquet_file_path}")
                data_frame.to_parquet(parquet_file)
            else:
                log.debug(f"Saving table {name} in {table.survey.hdf5_file_path}")
                to_hdf_kwargs = kwargs.pop("to_hdf_kwargs", {})
                table.save_data_frame_to_hdf5(data_frame, **to_hdf_kwargs)

        if name not in self.tables:
            self.tables[name] = {}
        for key, val in kwargs.items():
            self.tables[name][key] = val

    def to_json(self) -> dict:
        self_json = collections.OrderedDict(())
        self_json["hdf5_file_path"] = str(self.hdf5_file_path) if self.hdf5_file_path else None
        self_json["parquet_file_path"] = str(self.parquet_file_path) if self.parquet_file_path else None
        self_json["label"] = self.label
        self_json["name"] = self.name
        self_json["tables"] = self.tables
        self_json["informations"] = collections.OrderedDict(sorted(self.informations.items()))
        return self_json
