

"""
Example from page 23 of calmar documentation
https://www.insee.fr/fr/statistiques/fichier/2021902/doccalmar.pdf
"""

import numpy as np
import pandas as pd


from openfisca_survey_manager.calmar import calmar


def create_input_dataframe(entities = 1):
    columns = ['X', 'Y', 'Z', 'POND', 'id_variable']
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
    df1 = pd.DataFrame(columns = columns, index = index)
    values_by_index = {
        'A': [1, 1, 1, 10, 'A'],
        'B': [1, 2, 2, 0, 'B'],
        'C': [1, 2, 3, np.nan, 'C'],
        'D': [2, 1, 1, 11, 'D'],
        'E': [2, 1, 3, 13, 'E'],
        'F': [2, 2, 2, 7, 'F'],
        'G': [2, 2, 2, 8, 'G'],
        'H': [1, 2, 2, 8, 'H'],
        'I': [2, 1, 2, 9, 'I'],
        'J': [np.nan, 2, 2, 10, 'J'],
        'K': [2, 2, 2, 14, 'K'],
        }
    for index, values in values_by_index.items():
        df1.loc[index] = pd.Series(dict(zip(columns, values)))
    df1['Z'] = df1.Z.astype(float)
    df1['X'] = df1.X.astype(float)
    df1['POND'] = df1.POND.astype(float)
    df = {"main_entity": df1, "target_entity_name": "main_entity"}

    if entities == 2:
        columns2 = ['A', 'B', 'C', 'D', 'id_variable']
        index2 = [
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            ]
        df2 = pd.DataFrame(columns = columns2, index = index2)
        values_by_index2 = {
            0: [1, 1, 1, 10, "A"],
            1: [1, 2, 0, 0, "A"],
            2: [1, 2, 3, np.nan, "B"],
            3: [2, 1, 1, 11, "C"],
            4: [2, 1, 3, 13, "C"],
            5: [2, 2, 2, 7, "C"],
            6: [2, 2, 5, 8, "D"],
            7: [1, 2, 2, 8, "E"],
            8: [2, 1, 2, 9, "E"],
            9: [np.nan, 2, 2, 10, "F"],
            10: [2, 2, 2, 14, "G"],
            11: [1, 2, 3, 7, "G"],
            12: [2, 2, 8, 7, "H"],
            13: [1, 1, 3, 7, "I"],
            14: [1, 2, 4, 7, "I"],
            15: [2, 1, 0, 7, "J"],
            16: [2, 2, 3, 7, "K"],
            }
        for index, values in values_by_index2.items():
            df2.loc[index] = pd.Series(dict(zip(columns2, values)))

        df = {"main_entity": df1, "target_entity_name": "main_entity", "second_entity": df2}
    return df


def create_margins(entities = 1):
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
    if entities == 2:
        margins_by_variable['C'] = 85
        margins_by_variable['total_population'] = 80
        margins_by_variable['total_population_smaller_entity'] = 100
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

    data = create_input_dataframe(1)
    margins_by_variable = create_margins(1)
    pondfin_out, lambdasol, margins_new_dict = calmar(data, margins_by_variable, method = 'raking ratio', initial_weight = 'POND')

    data[data["target_entity_name"]]['weight_ratio'] = pondfin_out / data[data["target_entity_name"]].POND
    weight_ratio = data[data["target_entity_name"]].sort_values(['X', 'Y', 'Z'])['weight_ratio'].round(5)
    null_target_weight_ratio = target_weight_ratio.isnull()

    assert weight_ratio.loc[null_target_weight_ratio.values].isnull().all(), "Error on Nan"

    assert (
        target_weight_ratio.loc[~null_target_weight_ratio.values].values
        == weight_ratio.loc[~null_target_weight_ratio.values].values
        ).all(), "Errors on non NaN values"


def test_calmar_2_entities():

    data = create_input_dataframe(2)
    margins_by_variable = create_margins(2)
    pondfin_out, lambdasol, margins_new_dict = calmar(data, margins_by_variable, method = 'raking ratio', initial_weight = 'POND', )
    pondfin_out[np.isnan(pondfin_out)] = 0

    data["main_entity"]["final_pond"] = pondfin_out
    pondfin_ind = data["main_entity"].merge(data["second_entity"], on = "id_variable")["final_pond"]

    assert -1 < sum(pondfin_out) - 80 < 1
    assert -5 < sum(pondfin_ind) - 100 < 5


if __name__ == '__main__':
    import logging
    import sys
    log = logging.getLogger(__name__)
    verbose = True
    logging.basicConfig(level = logging.DEBUG, stream = sys.stdout)
    test_calmar()
