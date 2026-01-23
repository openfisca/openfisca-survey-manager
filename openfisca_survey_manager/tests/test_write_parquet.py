import pandas as pd
from pathlib import Path

from openfisca_survey_manager.scripts.build_collection import build_survey_collection


def test_write_parquet_one_file_per_entity(tmp_path: Path):
    data_dir = tmp_path / "test_parquet_collection"
    data_dir.mkdir()

    df = pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4],
            "rent": [1100, 2200, 3_000, 4_000],
            "household_weight": [550, 1500, 700, 200],
            "accommodation_size": [50, 100, 150, 200],
        }
    )
    filepath = data_dir / "household.parquet"
    df.to_parquet(filepath)
    df = pd.DataFrame(
        {
            "person_id": [11, 22, 33, 44, 55],
            "household_id": [1, 1, 2, 3, 4],
            "salary": [1300, 20, 3400, 4_000, 5_000],
            "person_weight": [500, 50, 1500, 700, 200],
            "household_role_index": [0, 1, 0, 0, 0],
        }
    )
    filepath = data_dir / "person.parquet"
    df.to_parquet(filepath)
    df2 = pd.read_parquet(filepath)
    assert df.equals(df2)


def test_write_parquet_multiple_files_per_entity(tmp_path: Path):
    collection_name = "test_multiple_parquet_collection"
    data_dir = tmp_path / collection_name

    (data_dir / "person").mkdir(parents=True)
    (data_dir / "household").mkdir(parents=True)

    # Create a file config.ini in the current directory
    config = data_dir / "config.ini"

    with open(config, "w") as f:
        f.write(
            f"""
[collections]
collections_directory = {data_dir}
{collection_name} = {data_dir}/{collection_name}.json

[data]
output_directory = {data_dir}
tmp_directory = {data_dir / "tmp"}
"""
        )
    (data_dir / "tmp").mkdir()

    # Create a file test_parquet_collection.json in the current directory
    json_file = data_dir / f"{collection_name}.json"

    with open(json_file, "w") as f:
        f.write(
            """
{
"label": "Test parquet collection",
"name": "collection_name",
"surveys": {
}
}
""".replace("collection_name", collection_name)
        )
    df = pd.DataFrame(
        {
            "household_id": [1, 2],
            "rent": [1100, 2200],
            "household_weight": [550, 1500],
            "accommodation_size": [50, 100],
        }
    )
    filepath = data_dir / "household" / "household-0.parquet"
    df.to_parquet(filepath)
    df = pd.DataFrame(
        {
            "household_id": [3, 4],
            "rent": [3_000, 4_000],
            "household_weight": [700, 200],
            "accommodation_size": [150, 200],
        }
    )
    filepath = data_dir / "household" / "household-1.parquet"
    df.to_parquet(filepath)
    df = pd.DataFrame(
        {
            "person_id": [11, 22],
            "household_id": [1, 1],
            "salary": [1300, 20],
            "person_weight": [500, 50],
            "household_role_index": [0, 1],
        }
    )
    filepath = data_dir / "person" / "person-0.parquet"
    df.to_parquet(filepath)
    df = pd.DataFrame(
        {
            "person_id": [33, 44, 55],
            "household_id": [2, 3, 4],
            "salary": [3400, 4_000, 5_000],
            "person_weight": [1500, 700, 200],
            "household_role_index": [0, 0, 0],
        }
    )
    filepath = data_dir / "person" / "person-1.parquet"
    df.to_parquet(filepath)
    df2 = pd.read_parquet(filepath)
    assert df.equals(df2)

    data_directory_path_by_survey_suffix = {
        "2020": str(data_dir),
    }
    build_survey_collection(
        collection_name=collection_name,
        data_directory_path_by_survey_suffix=data_directory_path_by_survey_suffix,
        replace_metadata=False,
        replace_data=False,
        source_format="parquet",
        config_files_directory=str(data_dir),
        keep_original_parquet_file=True,
    )
