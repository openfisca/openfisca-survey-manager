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
    df = pd.DataFrame({'household_id': [1, 2, 3, 4], 'rent': [1100, 2200, 3_000, 4_000], 'household_weight': [550, 1500, 700, 200], 'accommodation_size': [50, 100, 150, 200]})
    filepath = os.path.join(data_dir, 'household.parquet')
    df.to_parquet(filepath)
    df = pd.DataFrame({'person_id': [11, 22, 33, 44, 55], 'household_id': [1, 1, 2, 3, 4], 'salary': [1300, 20, 3400, 4_000, 5_000], 'person_weight': [500, 50, 1500, 700, 200], 'household_role_index': [0, 1, 0, 0, 0]})
    filepath = os.path.join(data_dir, 'person.parquet')
    df.to_parquet(filepath)
    df2 = pd.read_parquet(filepath)
    assert df.equals(df2)
