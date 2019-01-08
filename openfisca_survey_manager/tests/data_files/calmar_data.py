# -*- coding: utf-8 -*-


"""
Example from page 23 of calmar documentation
https://www.insee.fr/fr/statistiques/fichier/2021902/doccalmar.pdf
"""

import numpy as np
import pandas as pd


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
        'A': [1, 1, 1, 10,],
        'B': [1, 2, 2, 0,],
        'C': [1, 2, 3, np.nan,],
        'D': [2, 1, 1, 11,],
        'E': [2, 1, 3, 13,],
        'F': [2, 2, 2, 7,],
        'G': [2, 2, 2, 8,],
        'H': [1, 2, 2, 8,],
        'I': [2, 1, 2, 9,],
        'J': [np.nan, 2, 2, 10,],
        'K': [2, 2, 2, 14,],
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


if __name__ == '__main__':
    import logging
    import sys
    log = logging.getLogger(__name__)
    verbose = True
    logging.basicConfig(level = logging.DEBUG if verbose else logging.WARNING, stream = sys.stdout)

    data = create_input_dataframe()
    margins_by_variable = create_margins()
    print(data.info())
    print(margins_by_variable)
    from openfisca_survey_manager.calmar import calmar
    calmar(data, margins_by_variable, parameters = {'method': 'raking ratio'}, pondini = 'POND')

    BIM
    marges
# ;
# DATA MARGES;
# ;
# TITLE "Un petit exemple de calage sur marges";
# %CALMAR(DATA=DON,POIDS=POND,IDENT=NOM,
#  DATAMAR=MARGES,M=2,EDITPOI=OUI,OBSELI=OUI,
#  DATAPOI=SORTIE,POIDSFIN=PONDFIN,LABELPOI=pondération raking ratio)
# PROC PRINT DATA=__OBSELI;
# TITLE2 "Liste des observations éliminées";
