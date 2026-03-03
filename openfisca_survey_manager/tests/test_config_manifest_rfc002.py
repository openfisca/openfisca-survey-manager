"""Tests for RFC-002: config.yaml and manifest.yaml (new metadata architecture)."""

from pathlib import Path

import pytest

from openfisca_survey_manager.configuration.config_loader import (
    get_config_dir,
    load_config,
    load_manifest,
    manifest_survey_to_json,
)
from openfisca_survey_manager.configuration.paths import openfisca_survey_manager_location
from openfisca_survey_manager.core.dataset import SurveyCollection


@pytest.fixture
def rfc002_config_dir(tmp_path):
    """Create a config dir with config.yaml and a dataset with manifest.yaml."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        """
collections_dir: {collections}
default_output_dir: {output}
tmp_dir: {tmp}
""".format(
            collections=tmp_path / "collections",
            output=tmp_path / "output",
            tmp=tmp_path / "tmp",
        )
    )
    collections_dir = tmp_path / "collections"
    collections_dir.mkdir()
    dataset_dir = collections_dir / "test_dataset"
    dataset_dir.mkdir()
    (dataset_dir / "manifest.yaml").write_text(
        """
name: test_dataset
label: "Test dataset (RFC-002)"

surveys:
  survey_a:
    label: "Survey A"
    source:
      format: csv
      path: /data/survey_a
  survey_b:
    label: "Survey B"
    source:
      format: sas
      path: /data/survey_b
"""
    )
    return config_dir


def test_get_config_dir_explicit(tmp_path):
    assert get_config_dir(tmp_path) == tmp_path.resolve()


def test_get_config_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFISCA_SURVEY_CONFIG_DIR", str(tmp_path))
    assert get_config_dir() == tmp_path.resolve()


def test_load_config_missing(tmp_path):
    assert load_config(tmp_path) is None


def test_load_config_present(rfc002_config_dir):
    cfg = load_config(rfc002_config_dir)
    assert cfg is not None
    assert "collections_dir" in cfg
    assert "default_output_dir" in cfg
    assert cfg["collections_dir"].is_dir()
    assert (cfg["collections_dir"] / "test_dataset").is_dir()


def test_load_manifest_missing(tmp_path):
    assert load_manifest(tmp_path, "nonexistent") is None


def test_load_manifest_present(rfc002_config_dir):
    cfg = load_config(rfc002_config_dir)
    assert cfg is not None
    manifest = load_manifest(cfg["collections_dir"], "test_dataset")
    assert manifest is not None
    assert manifest["name"] == "test_dataset"
    assert manifest["label"] == "Test dataset (RFC-002)"
    assert "survey_a" in manifest["surveys"]
    assert manifest["surveys"]["survey_a"]["source"]["format"] == "csv"
    assert manifest["surveys"]["survey_a"]["source"]["path"] == "/data/survey_a"


def test_manifest_survey_to_json():
    entry = {
        "label": "My survey",
        "source": {"format": "sas", "path": "/path/to/data"},
    }
    out = manifest_survey_to_json("my_survey", entry)
    assert out["name"] == "my_survey"
    assert out["label"] == "My survey"
    assert out["informations"]["sas_files"] == ["/path/to/data"]


def test_survey_collection_load_from_manifest(rfc002_config_dir):
    """SurveyCollection.load(collection=..., config_files_directory=...) uses manifest when config.yaml exists."""
    col = SurveyCollection.load(
        collection="test_dataset",
        config_files_directory=rfc002_config_dir,
    )
    assert col.name == "test_dataset"
    assert col.label == "Test dataset (RFC-002)"
    assert col.config is None
    assert col.output_directory is not None
    assert len(col.surveys) == 2
    names = {s.name for s in col.surveys}
    assert names == {"survey_a", "survey_b"}
    survey_a = col.get_survey("survey_a")
    assert survey_a.label == "Survey A"
    assert survey_a.informations.get("csv_files") == ["/data/survey_a"]
    # Default store_format when missing in manifest is parquet
    assert survey_a.store_format == "parquet"
    assert survey_a.parquet_file_path is not None
    assert "survey_a" in survey_a.parquet_file_path


def test_survey_collection_load_from_manifest_store_format_zarr(tmp_path):
    """When manifest has store_format: zarr, surveys get zarr_file_path set."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        f"""
collections_dir: {tmp_path / "collections"}
default_output_dir: {tmp_path / "output"}
tmp_dir: {tmp_path / "tmp"}
"""
    )
    collections_dir = tmp_path / "collections"
    collections_dir.mkdir()
    dataset_dir = collections_dir / "zarr_dataset"
    dataset_dir.mkdir()
    (dataset_dir / "manifest.yaml").write_text(
        """
name: zarr_dataset
label: "Zarr dataset"
store_format: zarr
surveys:
  s1:
    label: "Survey 1"
    source:
      format: csv
      path: /data/s1
"""
    )
    col = SurveyCollection.load(
        collection="zarr_dataset",
        config_files_directory=config_dir,
    )
    assert col.output_directory is not None
    survey_s1 = col.get_survey("s1")
    assert survey_s1.store_format == "zarr"
    assert survey_s1.zarr_file_path is not None
    assert survey_s1.zarr_file_path.endswith(".zarr")
    assert survey_s1.hdf5_file_path is None
    assert survey_s1.parquet_file_path is None


def test_survey_collection_load_legacy_unchanged(tmp_path):
    """Legacy config.ini + JSON still works when config.yaml is absent (emits DeprecationWarning)."""
    # Use the package test data dir which has config.ini and fake.json
    tests_data = Path(openfisca_survey_manager_location) / "openfisca_survey_manager" / "tests" / "data_files"
    if not (tests_data / "config.ini").exists():
        pytest.skip("config.ini not present in tests/data_files")
    if not (tests_data / "fake.json").exists():
        pytest.skip("fake.json not present in tests/data_files")
    with pytest.warns(DeprecationWarning, match="config.ini and JSON files is deprecated"):
        col = SurveyCollection.load(
            collection="fake",
            config_files_directory=tests_data,
        )
    assert col.config is not None
    assert col.name == "fake"
    assert len(col.surveys) >= 0


# --- Migration script tests ---


@pytest.fixture
def legacy_config_dir(tmp_path):
    """Create a minimal legacy config dir: config.ini + one collection JSON."""
    config_dir = tmp_path / "legacy_config"
    config_dir.mkdir()
    collections_dir = tmp_path / "legacy_collections"
    collections_dir.mkdir()
    json_path = collections_dir / "my_collection.json"
    json_path.write_text(
        """
{
  "name": "my_collection",
  "label": "My collection",
  "surveys": {
    "survey_1": {
      "label": "Survey 1",
      "informations": {
        "csv_files": ["/data/s1/file1.csv"]
      }
    },
    "survey_2": {
      "label": "Survey 2",
      "informations": {
        "sas_files": ["/data/s2/file.sas7bdat"]
      }
    }
  }
}
""",
        encoding="utf-8",
    )
    config_ini = config_dir / "config.ini"
    config_ini.write_text(
        f"""[collections]
collections_directory = {collections_dir}
my_collection = {json_path}

[data]
output_directory = {tmp_path / "output"}
tmp_directory = /tmp
""",
        encoding="utf-8",
    )
    return config_dir


def test_migrate_produces_config_yaml_and_manifests(legacy_config_dir):
    """Migration script creates config.yaml and collection manifest."""
    from openfisca_survey_manager.scripts.migrate_config_to_rfc002 import (
        CONFIG_FILENAME,
        MANIFEST_FILENAME,
        migrate,
    )

    ok = migrate(legacy_config_dir, dry_run=False)
    assert ok is True
    config_yaml = legacy_config_dir / CONFIG_FILENAME
    assert config_yaml.is_file()
    cfg = load_config(legacy_config_dir)
    assert cfg is not None
    assert "collections_dir" in cfg
    assert (Path(cfg["collections_dir"]) / "my_collection" / MANIFEST_FILENAME).is_file()
    manifest = load_manifest(cfg["collections_dir"], "my_collection")
    assert manifest is not None
    assert manifest["name"] == "my_collection"
    assert manifest.get("store_format") == "parquet"
    assert manifest["surveys"]["survey_1"]["source"]["format"] == "csv"
    assert manifest["surveys"]["survey_1"]["source"]["path"] == "/data/s1/file1.csv"
    assert manifest["surveys"]["survey_2"]["source"]["format"] == "sas"
    assert manifest["surveys"]["survey_2"]["source"]["path"] == "/data/s2/file.sas7bdat"


def test_migrate_infers_store_format_from_legacy(tmp_path):
    """Migration infers store_format from legacy JSON (hdf5_file_path -> hdf5, etc.)."""
    from openfisca_survey_manager.scripts.migrate_config_to_rfc002 import (
        _infer_store_format_from_legacy,
        build_manifest_from_json,
    )

    # Legacy with parquet_file_path
    json_parquet = tmp_path / "p.json"
    json_parquet.write_text(
        '{"name":"p","label":"P","surveys":{"s1":{"label":"S1","parquet_file_path":"/out/s1"}}}',
        encoding="utf-8",
    )
    manifest_parquet = build_manifest_from_json(json_parquet, None)
    assert manifest_parquet["store_format"] == "parquet"

    # Legacy with hdf5_file_path only
    json_hdf5 = tmp_path / "h.json"
    json_hdf5.write_text(
        '{"name":"h","label":"H","surveys":{"s1":{"label":"S1","hdf5_file_path":"/out/s1.h5"}}}',
        encoding="utf-8",
    )
    manifest_hdf5 = build_manifest_from_json(json_hdf5, None)
    assert manifest_hdf5["store_format"] == "hdf5"

    # Infer function directly
    assert _infer_store_format_from_legacy({}) == "parquet"
    assert _infer_store_format_from_legacy({"s": {"zarr_file_path": "/z"}}) == "zarr"


def test_migrate_dry_run_does_not_write(legacy_config_dir):
    """Migration with --dry-run does not create files."""
    from openfisca_survey_manager.scripts.migrate_config_to_rfc002 import (
        CONFIG_FILENAME,
        migrate,
    )

    ok = migrate(legacy_config_dir, dry_run=True)
    assert ok is True
    assert not (legacy_config_dir / CONFIG_FILENAME).is_file()
