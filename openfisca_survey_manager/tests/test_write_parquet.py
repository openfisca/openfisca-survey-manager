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
    df = pd.DataFrame({'household_id': [1, 2], 'rent': [3300, 4400], 'household_weight': [550, 1500]})
    filepath = os.path.join(data_dir, 'household.parquet')
    df.to_parquet(filepath)
    df = pd.DataFrame({'household_id': [1, 1, 2], 'salary': [3300, 0, 4400], 'person_weight': [550, 0, 1500], 'household_role_index': [0, 1, 0]})
    filepath = os.path.join(data_dir, 'person.parquet')
    df.to_parquet(filepath)
    df2 = pd.read_parquet(filepath)
    assert df.equals(df2)
