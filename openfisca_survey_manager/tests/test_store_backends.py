"""Tests for store backends (HDF5, Parquet, Zarr)."""

from pathlib import Path

import pandas as pd
import pytest

from openfisca_survey_manager.io.backends import (
    get_available_backend_names,
    get_backend,
)


def test_get_backend_hdf5():
    backend = get_backend("hdf5")
    assert backend is not None
    assert hasattr(backend, "write_table") and hasattr(backend, "read_table")
    assert hasattr(backend, "table_exists")


def test_get_backend_parquet():
    backend = get_backend("parquet")
    assert backend is not None


def test_get_backend_invalid_raises():
    with pytest.raises(ValueError, match="Unknown store backend"):
        get_backend("invalid_format")


def test_parquet_backend_roundtrip(tmp_path):
    backend = get_backend("parquet")
    store_path = str(tmp_path / "survey")
    store_path_path = Path(store_path)
    store_path_path.mkdir(parents=True)
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    backend.write_table(store_path, "mytable", df)
    assert backend.table_exists(store_path, "mytable")
    df2 = backend.read_table(store_path, "mytable")
    pd.testing.assert_frame_equal(df, df2)
    df3 = backend.read_table(store_path, "mytable", variables=["a"])
    assert list(df3.columns) == ["a"]


def test_available_backends_include_hdf5_parquet():
    names = get_available_backend_names()
    assert "hdf5" in names
    assert "parquet" in names
    # zarr only if zarr package installed
    assert len(names) >= 2
