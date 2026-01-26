from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def parquet_data(tmp_path: Path):
    """Fixture to set up parquet data for tests."""
    data_dir = tmp_path
    collection_name = "test_parquet_collection"

    # Setup single file per entity collection
    collection_dir = data_dir / collection_name
    collection_dir.mkdir()

    df_household = pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4],
            "rent": [1100, 2200, 3_000, 4_000],
            "household_weight": [550, 1500, 700, 200],
            "accommodation_size": [50, 100, 150, 200],
        }
    )
    df_household.to_parquet(collection_dir / "household.parquet")

    df_person = pd.DataFrame(
        {
            "person_id": [11, 22, 33, 44, 55],
            "household_id": [1, 1, 2, 3, 4],
            "salary": [1300, 20, 3400, 4_000, 5_000],
            "person_weight": [500, 50, 1500, 700, 200],
            "household_role_index": [0, 1, 0, 0, 0],
        }
    )
    df_person.to_parquet(collection_dir / "person.parquet")

    # Setup Json for single file collection
    json_file = data_dir / f"{collection_name}.json"
    with json_file.open("w") as f:
        f.write(f"""
    {{
    "label": "Test parquet collection",
    "name": "{collection_name}",
    "surveys": {{
    }}
    }}
    """)

    # Config for single
    config_single = data_dir / "config.ini"
    with config_single.open("w") as f:
        f.write(f"""
[collections]
collections_directory = {data_dir}
{collection_name} = {data_dir}/{collection_name}.json

[data]
output_directory = {data_dir}
tmp_directory = {data_dir / "tmp"}
""")
    (data_dir / "tmp").mkdir(exist_ok=True)

    # Setup multiple files per entity collection
    multi_collection_name = "test_multiple_parquet_collection"
    multi_dir = data_dir / multi_collection_name
    (multi_dir / "person").mkdir(parents=True)
    (multi_dir / "household").mkdir(parents=True)

    # Config for multiple
    config = multi_dir / "config.ini"
    with config.open("w") as f:
        f.write(f"""
[collections]
collections_directory = {multi_dir}
{multi_collection_name} = {multi_dir}/{multi_collection_name}.json

[data]
output_directory = {multi_dir}
tmp_directory = {multi_dir / "tmp"}
""")
    (multi_dir / "tmp").mkdir(exist_ok=True)

    # Json for multiple
    json_file_multi = multi_dir / f"{multi_collection_name}.json"
    with json_file_multi.open("w") as f:
        f.write(f"""
    {{
    "label": "Test parquet collection",
    "name": "{multi_collection_name}",
    "surveys": {{
    }}
    }}
    """)

    # Data for multiple
    df_h1 = pd.DataFrame(
        {
            "household_id": [1, 2],
            "rent": [1100, 2200],
            "household_weight": [550, 1500],
            "accommodation_size": [50, 100],
        }
    )
    df_h1.to_parquet(multi_dir / "household" / "household-0.parquet")

    df_h2 = pd.DataFrame(
        {
            "household_id": [3, 4],
            "rent": [3_000, 4_000],
            "household_weight": [700, 200],
            "accommodation_size": [150, 200],
        }
    )
    df_h2.to_parquet(multi_dir / "household" / "household-1.parquet")

    df_p1 = pd.DataFrame(
        {
            "person_id": [11, 22],
            "household_id": [1, 1],
            "salary": [1300, 20],
            "person_weight": [500, 50],
            "household_role_index": [0, 1],
        }
    )
    df_p1.to_parquet(multi_dir / "person" / "person-0.parquet")

    df_p2 = pd.DataFrame(
        {
            "person_id": [33, 44, 55],
            "household_id": [2, 3, 4],
            "salary": [3400, 4_000, 5_000],
            "person_weight": [1500, 700, 200],
            "household_role_index": [0, 0, 0],
        }
    )
    df_p2.to_parquet(multi_dir / "person" / "person-1.parquet")

    return data_dir
