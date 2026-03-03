#!/usr/bin/env python
"""
Migrate existing config (config.ini + raw_data.ini + JSON collections) to RFC-002 layout.

Produces:
  - config.yaml (collections_dir, default_output_dir, tmp_dir)
  - collections_dir/<name>/manifest.yaml per collection

Usage:
  python -m openfisca_survey_manager.scripts.migrate_config_to_rfc002 [--config-dir PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import configparser
import json
import logging
import sys
from pathlib import Path

import yaml

# Allow running as __main__ or as script
try:
    from openfisca_survey_manager.configuration.config_loader import (
        CONFIG_FILENAME,
        MANIFEST_FILENAME,
    )
except ImportError:
    CONFIG_FILENAME = "config.yaml"
    MANIFEST_FILENAME = "manifest.yaml"

log = logging.getLogger(__name__)

SOURCE_FORMAT_KEYS = ("csv_files", "sas_files", "stata_files", "parquet_files")


def _informations_to_source(informations: dict) -> tuple[str, str]:
    """From Survey.informations (e.g. csv_files, sas_files), return (format, path)."""
    if not informations:
        return "csv", ""
    for key in SOURCE_FORMAT_KEYS:
        paths = informations.get(key)
        if paths and isinstance(paths, list) and len(paths) > 0:
            fmt = key.replace("_files", "")
            path = paths[0] if isinstance(paths[0], str) else str(paths[0])
            return fmt, path
    return "csv", ""


def build_manifest_from_json(
    json_path: Path,
    raw_data_section: dict[str, str] | None = None,
) -> dict:
    """
    Build RFC-002 manifest dict from a legacy collection JSON file.
    raw_data_section: optional dict survey_name -> path from raw_data.ini [collection_name].
    """
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)
    name = data.get("name", json_path.stem)
    label = data.get("label", name)
    surveys_data = data.get("surveys", {})
    if not isinstance(surveys_data, dict):
        surveys_data = {}
    surveys = {}
    for survey_name, survey_obj in surveys_data.items():
        if not isinstance(survey_obj, dict):
            continue
        infos = survey_obj.get("informations", {}) or {}
        if raw_data_section and survey_name in raw_data_section:
            path = raw_data_section[survey_name]
            fmt = "csv"
            for k in SOURCE_FORMAT_KEYS:
                if infos.get(k):
                    fmt = k.replace("_files", "")
                    break
        else:
            fmt, path = _informations_to_source(infos)
        surveys[survey_name] = {
            "label": survey_obj.get("label", survey_name),
            "source": {"format": fmt, "path": path},
        }
        if survey_obj.get("output_subdir"):
            surveys[survey_name]["output_subdir"] = survey_obj["output_subdir"]

    store_format = _infer_store_format_from_legacy(surveys_data)
    return {"name": name, "label": label, "store_format": store_format, "surveys": surveys}


def _infer_store_format_from_legacy(surveys_data: dict) -> str:
    """Infer store_format from legacy JSON surveys (parquet_file_path, zarr_file_path, hdf5_file_path)."""
    if not isinstance(surveys_data, dict):
        return "parquet"
    for survey_obj in surveys_data.values():
        if not isinstance(survey_obj, dict):
            continue
        if survey_obj.get("zarr_file_path"):
            return "zarr"
        if survey_obj.get("parquet_file_path"):
            return "parquet"
        if survey_obj.get("hdf5_file_path"):
            return "hdf5"
    return "parquet"


def load_raw_data_ini(config_dir: Path) -> configparser.ConfigParser | None:
    """Load raw_data.ini if present."""
    path = config_dir / "raw_data.ini"
    if not path.is_file():
        return None
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    return parser


def migrate(
    config_dir: Path,
    *,
    dry_run: bool = False,
) -> bool:
    """
    Migrate config_dir from config.ini (+ raw_data.ini + JSON) to config.yaml + manifests.
    Returns True if migration was done (or dry_run succeeded).
    """
    config_ini = config_dir / "config.ini"
    if not config_ini.is_file():
        log.error("No config.ini found in %s", config_dir)
        return False

    parser = configparser.ConfigParser()
    parser.read(config_ini, encoding="utf-8")
    if "collections" not in parser.sections():
        log.error("config.ini has no [collections] section")
        return False

    collections_dir_str = parser.get("collections", "collections_directory", fallback=None)
    if not collections_dir_str:
        collections_dir_str = str(config_dir / "collections")
    collections_dir = Path(collections_dir_str).expanduser().resolve()

    output_dir = parser.get("data", "output_directory", fallback=str(config_dir / "output"))
    tmp_dir = parser.get("data", "tmp_directory", fallback="/tmp")
    if "data" not in parser.sections():
        output_dir = str(config_dir / "output")
        tmp_dir = "/tmp"

    raw_data = load_raw_data_ini(config_dir)
    collection_names: list[str] = []
    for key in parser.options("collections"):
        if key == "collections_directory":
            continue
        collection_names.append(key)

    if not collection_names:
        log.warning("No collection entries in config.ini (only collections_directory)")
        # Still write config.yaml so the dir is ready for new-style use
    else:
        if not dry_run:
            collections_dir.mkdir(parents=True, exist_ok=True)
        for name in collection_names:
            try:
                json_path_str = parser.get("collections", name)
            except configparser.NoOptionError:
                continue
            json_path = Path(json_path_str).expanduser().resolve()
            if not json_path.is_file():
                log.warning("Collection %s: JSON file not found %s", name, json_path)
                continue
            raw_section = None
            if raw_data and raw_data.has_section(name):
                raw_section = dict(raw_data.items(name))
            manifest = build_manifest_from_json(json_path, raw_section)
            manifest_path = collections_dir / name / MANIFEST_FILENAME
            if dry_run:
                log.info("[dry-run] Would write %s", manifest_path)
                continue
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with manifest_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(
                    manifest,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            log.info("Wrote %s", manifest_path)

    config_yaml_path = config_dir / CONFIG_FILENAME
    new_config = {
        "collections_dir": str(collections_dir),
        "default_output_dir": str(Path(output_dir).expanduser().resolve()),
        "tmp_dir": str(Path(tmp_dir).expanduser().resolve()),
    }
    if dry_run:
        log.info("[dry-run] Would write %s with %s", config_yaml_path, new_config)
        return True
    with config_yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(new_config, f, default_flow_style=False, sort_keys=False)
    log.info("Wrote %s", config_yaml_path)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Migrate config.ini + raw_data.ini + JSON to RFC-002 (config.yaml + manifests)",
    )
    ap.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing config.ini (default: XDG or OPENFISCA_SURVEY_CONFIG_DIR)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Only log what would be done",
    )
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = ap.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )
    if args.config_dir is None:
        try:
            from openfisca_survey_manager.configuration.config_loader import (
                get_config_dir,
            )

            config_dir = get_config_dir()
        except Exception:
            log.error("Provide --config-dir or set OPENFISCA_SURVEY_CONFIG_DIR")
            return 1
    else:
        config_dir = args.config_dir.expanduser().resolve()
    if not config_dir.is_dir():
        log.error("Config directory does not exist: %s", config_dir)
        return 1
    ok = migrate(config_dir, dry_run=args.dry_run)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
