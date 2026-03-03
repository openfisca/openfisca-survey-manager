"""RFC-002: New config and manifest loading (YAML-based)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from xdg import BaseDirectory

log = logging.getLogger(__name__)

CONFIG_FILENAME = "config.yaml"
MANIFEST_FILENAME = "manifest.yaml"
ENV_CONFIG_DIR = "OPENFISCA_SURVEY_CONFIG_DIR"


def get_config_dir(explicit: Optional[Path | str] = None) -> Path:
    """Return config directory: explicit path, or env OPENFISCA_SURVEY_CONFIG_DIR, or XDG."""
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    import os

    env_path = os.environ.get(ENV_CONFIG_DIR)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(BaseDirectory.save_config_path("openfisca-survey-manager"))


def load_config(config_dir: Path) -> Optional[dict[str, Any]]:
    """
    Load new-style config from config_dir/config.yaml.
    Returns dict with collections_dir, default_output_dir, tmp_dir (paths expanded),
    or None if config.yaml is missing or invalid.
    """
    config_path = config_dir / CONFIG_FILENAME
    if not config_path.is_file():
        return None
    try:
        with config_path.open() as f:
            data = yaml.safe_load(f)
    except Exception as e:
        log.warning("Failed to load %s: %s", config_path, e)
        return None
    if not data or not isinstance(data, dict):
        return None
    collections_dir = data.get("collections_dir")
    if not collections_dir:
        return None
    out = {
        "collections_dir": Path(collections_dir).expanduser().resolve(),
        "default_output_dir": Path(data.get("default_output_dir", ".")).expanduser().resolve(),
        "tmp_dir": Path(data.get("tmp_dir", "/tmp")).expanduser().resolve(),
    }
    return out


def load_manifest(collections_dir: Path, name: str) -> Optional[dict[str, Any]]:
    """
    Load dataset manifest from collections_dir/name/manifest.yaml.
    Returns manifest dict (name, label, surveys) or None if missing.
    """
    manifest_path = collections_dir / name / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return None
    try:
        with manifest_path.open() as f:
            data = yaml.safe_load(f)
    except Exception as e:
        log.warning("Failed to load manifest %s: %s", manifest_path, e)
        return None
    if not data or not isinstance(data, dict) or "surveys" not in data:
        return None
    return data


def manifest_survey_to_json(survey_name: str, entry: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a manifest survey entry to the dict shape expected by Survey.create_from_json.
    entry: { label?, source: { format, path }, output_subdir? }
    """
    source = entry.get("source") or {}
    fmt = source.get("format", "csv")
    path = source.get("path", "")
    # Survey expects e.g. csv_files, sas_files list in informations
    files_key = f"{fmt}_files"
    informations = {files_key: [path] if path else []}
    return {
        "name": survey_name,
        "label": entry.get("label", survey_name),
        "hdf5_file_path": None,
        "parquet_file_path": None,
        "tables": entry.get("tables"),
        "informations": informations,
    }
