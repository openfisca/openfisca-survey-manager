import pandas as pd
import os
from openfisca_survey_manager import openfisca_survey_manager_location


def test_write_parquet():
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        'test_parquet_collection',
        )
    df = pd.DataFrame({'household_id': [1, 2, 3, 4], 'rent': [3300, 4400, 5_000, 6_000], 'household_weight': [550, 1500, 700, 200]})
    filepath = os.path.join(data_dir, 'household.parquet')
    df.to_parquet(filepath)
    df = pd.DataFrame({'household_id': [1, 1, 2, 3, 4], 'salary': [3300, 0, 4400, 2_000, 8_000], 'person_weight': [500, 50, 1500, 700, 200], 'household_role_index': [0, 1, 0, 0, 0]})
    filepath = os.path.join(data_dir, 'person.parquet')
    df.to_parquet(filepath)
    df2 = pd.read_parquet(filepath)
    assert df.equals(df2)
