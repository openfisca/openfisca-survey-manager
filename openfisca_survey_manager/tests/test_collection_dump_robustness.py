"""SurveyCollection.dump robustness: Path-safe serialization and atomic write.

Regression tests for a silent data-corruption bug: when a ``pathlib.Path``
value ended up in table metadata (e.g. ``parquet_file`` set by
``set_table_in_survey``), ``dump`` opened the collection JSON for writing and
then raised ``TypeError: Object of type PosixPath is not JSON serializable``
MID-WRITE, leaving a truncated file on disk — every subsequent load of the
collection then failed with ``JSONDecodeError``.
"""

import json
from pathlib import Path

from openfisca_survey_manager.core.dataset import SurveyCollection
from openfisca_survey_manager.core.survey import Survey


def _collection(tmp_path, json_name="collection.json"):
    collection = SurveyCollection(name="test_collection")

    # Minimal config stub honouring the two calls made by dump().
    class _ConfigStub:
        def set(self, *args, **kwargs):
            return None

        def save(self):
            return None

    collection.config = _ConfigStub()
    collection.json_file_path = str(tmp_path / json_name)
    return collection


def test_dump_serializes_path_values_as_strings(tmp_path):
    collection = _collection(tmp_path)
    survey = Survey(name="test_survey")
    survey.tables = {
        "table_2021": {
            "source_format": "parquet",
            # The problematic payload: a pathlib.Path in table metadata.
            "parquet_file": Path(tmp_path) / "table_2021.parquet",
        }
    }
    collection.surveys = [survey]

    collection.dump()

    with Path(collection.json_file_path).open(encoding="utf-8") as _file:
        payload = json.load(_file)  # valid JSON, no truncation
    [survey_json] = payload["surveys"].values() if isinstance(payload["surveys"], dict) else payload["surveys"]
    table = survey_json["tables"]["table_2021"]
    assert table["parquet_file"] == str(Path(tmp_path) / "table_2021.parquet")


def test_dump_failure_does_not_truncate_existing_file(tmp_path):
    collection = _collection(tmp_path)
    collection.surveys = []
    collection.dump()
    original = Path(collection.json_file_path).read_text(encoding="utf-8")
    json.loads(original)  # sanity: valid

    # Make serialization fail hard AFTER the file exists: to_json raising
    # must leave the previous valid file untouched (atomic write).
    class _Boom(SurveyCollection):
        def to_json(self):
            raise RuntimeError("serialization exploded")

    broken = _Boom(name="test_collection")
    broken.config = collection.config
    broken.json_file_path = collection.json_file_path
    try:
        broken.dump()
    except RuntimeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError")

    assert Path(collection.json_file_path).read_text(encoding="utf-8") == original
    # and no temp file left behind
    leftovers = list(Path(tmp_path).glob("*.tmp"))
    assert leftovers == []
