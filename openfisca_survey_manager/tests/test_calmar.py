

"""
Example from page 23 of calmar documentation
https://www.insee.fr/fr/statistiques/fichier/2021902/doccalmar.pdf
"""

import numpy as np
import pandas as pd


from openfisca_survey_manager.calmar import calmar


def create_input_dataframe():
    columns = ['X', 'Y', 'Z', 'POND']
    index = [
        'A',
        'B',
        'C',
        'D',
        'E',
        'F',
        'G',
        'H',
        'I',
        'J',
        'K',
        ]
    df = pd.DataFrame(columns = columns, index = index)
    values_by_index = {
        'A': [1, 1, 1, 10],
        'B': [1, 2, 2, 0],
        'C': [1, 2, 3, np.nan],
        'D': [2, 1, 1, 11],
        'E': [2, 1, 3, 13],
        'F': [2, 2, 2, 7],
        'G': [2, 2, 2, 8],
        'H': [1, 2, 2, 8],
        'I': [2, 1, 2, 9],
        'J': [np.nan, 2, 2, 10],
        'K': [2, 2, 2, 14],
        }
    for index, values in values_by_index.items():
        df.loc[index] = pd.Series(dict(zip(columns, values)))

    df['Z'] = df.Z.astype(float)
    df['POND'] = df.POND.astype(float)
    return df


def create_margins():
    margins_by_variable = {
        'X': {
            1: 20,
            2: 60,
            },
        'Y': {
            1: 30,
            2: 50,
            },
        'Z': 140.0
        }
    return margins_by_variable


def test_calmar():
    target_weight_ratio = pd.Series([
        1.01683,
        np.nan,
        1.22897,
        np.nan,
        1.14602,
        0.49456,
        0.21342,
        1.38511,
        1.38511,
        1.38511,
        1.00000,
        ])

    data = create_input_dataframe()
    margins_by_variable = create_margins()
    pondfin_out, lambdasol, margins_new_dict = calmar(data, margins_by_variable, method = 'raking ratio', initial_weight = 'POND')

    data['weightt_ratio'] = pondfin_out / data.POND
    weight_ratio = data.sort_values(['X', 'Y', 'Z'])['weightt_ratio'].round(5)
    null_target_weight_ratio = target_weight_ratio.isnull()

    assert weight_ratio.loc[null_target_weight_ratio.values].isnull().all(), "Error on Nan"

    assert (
        target_weight_ratio.loc[~null_target_weight_ratio.values].values
        == weight_ratio.loc[~null_target_weight_ratio.values].values
        ).all(), "Erros on non NaN values"


if __name__ == '__main__':
    import logging
    import sys
    log = logging.getLogger(__name__)
    verbose = True
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_calmar()
