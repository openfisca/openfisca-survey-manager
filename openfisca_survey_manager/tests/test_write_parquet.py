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
    df = pd.DataFrame({'id_foy': [1, 2], 'irpp_economique': [3300, 4400], 'rfr': [550, 1500]})
    filepath = os.path.join(data_dir, 'foyer.parquet')
    df.to_parquet(filepath)
    df = pd.DataFrame({'id_foy': [1, 1, 2], 'salaire': [3300, 0, 4400], 'rente': [550, 0, 1500]})
    filepath = os.path.join(data_dir, 'individus.parquet')
    df.to_parquet(filepath)
    df2 = pd.read_parquet(filepath)
    assert df.equals(df2)
