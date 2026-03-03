"""Store backends for survey tables: HDF5, Parquet, Zarr.

Allows choosing the storage format (backend) when building or filling the store.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Protocol

import pandas as pd

from openfisca_survey_manager.io.hdf import hdf5_safe_key, write_table_to_hdf5
from openfisca_survey_manager.io.writers import write_table_to_parquet

log = logging.getLogger(__name__)


# Supported store format names (zarr only if zarr package is installed)
def get_available_backend_names() -> tuple[str, ...]:
    return tuple(_backends.keys())


class StoreBackend(Protocol):
    """Protocol for a store backend (write/read tables)."""

    def write_table(
        self,
        store_path: str,
        table_name: str,
        data_frame: pd.DataFrame,
        **kwargs: Any,
    ) -> Optional[str]:
        """Write a table. Returns path used for the table (e.g. file path) or None."""
        ...

    def read_table(
        self,
        store_path: str,
        table_name: str,
        variables: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Read a table as DataFrame."""
        ...

    def table_exists(self, store_path: str, table_name: str) -> bool:
        """Return True if the table exists in the store."""
        ...


class HDF5Backend:
    """Store tables in a single HDF5 file."""

    def write_table(
        self,
        store_path: str,
        table_name: str,
        data_frame: pd.DataFrame,
        **kwargs: Any,
    ) -> Optional[str]:
        write_table_to_hdf5(
            data_frame,
            hdf5_file_path=store_path,
            store_path=table_name,
            **kwargs,
        )
        return None

    def read_table(
        self,
        store_path: str,
        table_name: str,
        variables: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        key = hdf5_safe_key(table_name)
        store = pd.HDFStore(store_path, "r")
        try:
            df = store.select(key)
        finally:
            store.close()
        if variables is not None:
            df = df[[c for c in variables if c in df.columns]]
        return df

    def table_exists(self, store_path: str, table_name: str) -> bool:
        if not Path(store_path).is_file():
            return False
        key = hdf5_safe_key(table_name)
        store = pd.HDFStore(store_path, "r")
        try:
            keys = store.keys()
            return key in keys or any(k.lstrip("/") == key for k in keys)
        finally:
            store.close()


class ParquetBackend:
    """Store each table as a parquet file in a directory (store_path/table_name.parquet)."""

    def write_table(
        self,
        store_path: str,
        table_name: str,
        data_frame: pd.DataFrame,
        **kwargs: Any,
    ) -> Optional[str]:
        return write_table_to_parquet(
            data_frame,
            parquet_dir_path=store_path,
            table_name=table_name,
        )

    def read_table(
        self,
        store_path: str,
        table_name: str,
        variables: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        path = Path(store_path) / f"{table_name}.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"No table {table_name} at {path}")
        return pd.read_parquet(path, columns=variables)

    def table_exists(self, store_path: str, table_name: str) -> bool:
        return (Path(store_path) / f"{table_name}.parquet").is_file()


def _write_table_to_zarr(
    data_frame: pd.DataFrame,
    zarr_dir_path: str,
    table_name: str,
) -> str:
    """Write a DataFrame to a zarr group (store_path/table_name)."""
    import pandas as pd

    zarr_path = str(Path(zarr_dir_path) / table_name)
    Path(zarr_path).parent.mkdir(parents=True, exist_ok=True)
    # Object columns can cause issues; coerce to string like parquet backend
    for col in data_frame.columns:
        if data_frame[col].dtype == "object":
            try:
                data_frame[col] = data_frame[col].astype(str)
            except Exception:
                data_frame[col] = data_frame[col].apply(lambda x: str(x) if pd.notna(x) else None)
    data_frame.to_zarr(zarr_path, mode="w")
    return zarr_path


def _read_table_from_zarr(
    zarr_dir_path: str,
    table_name: str,
    variables: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Read a table from a zarr group."""
    zarr_path = str(Path(zarr_dir_path) / table_name)
    df = pd.read_zarr(zarr_path)
    if variables is not None:
        df = df[[c for c in variables if c in df.columns]]
    return df


class ZarrBackend:
    """Store each table as a zarr group in a directory (store_path/table_name)."""

    def write_table(
        self,
        store_path: str,
        table_name: str,
        data_frame: pd.DataFrame,
        **kwargs: Any,
    ) -> Optional[str]:
        return _write_table_to_zarr(data_frame, store_path, table_name)

    def read_table(
        self,
        store_path: str,
        table_name: str,
        variables: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        return _read_table_from_zarr(store_path, table_name, variables)

    def table_exists(self, store_path: str, table_name: str) -> bool:
        return (Path(store_path) / table_name).is_dir()


def _build_backends() -> dict[str, StoreBackend]:
    backends: dict[str, StoreBackend] = {
        "hdf5": HDF5Backend(),
        "parquet": ParquetBackend(),
    }
    try:
        import zarr  # noqa: F401

        backends["zarr"] = ZarrBackend()
    except ImportError:
        log.debug("zarr not installed; zarr store backend unavailable")
    return backends


_backends = _build_backends()

STORE_BACKEND_NAMES = get_available_backend_names()

__all__ = [
    "get_backend",
    "get_available_backend_names",
    "register_backend",
    "StoreBackend",
    "STORE_BACKEND_NAMES",
]


def get_backend(name: str) -> StoreBackend:
    """Return the store backend for the given format name."""
    if name not in _backends:
        raise ValueError(f"Unknown store backend: {name}. Choose from {list(_backends.keys())}")
    return _backends[name]


def register_backend(name: str, backend: StoreBackend) -> None:
    """Register a custom store backend (e.g. for testing or extensions)."""
    _backends[name] = backend
