import pandas as pd
import os
from openfisca_survey_manager import openfisca_survey_manager_location


def test_write_parquet():
    data_dir = os.path.join(
        openfisca_survey_manager_location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )
    filepath = os.path.join(data_dir, 'test.parquet')
    df = pd.DataFrame({'revenue': [3300, 4400], 'rfr': [550, 1500]})

    df.to_parquet(filepath)
    df2 = pd.read_parquet(filepath)
    assert df.equals(df2)
