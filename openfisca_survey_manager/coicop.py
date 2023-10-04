import logging
import os
import pandas as pd


from openfisca_survey_manager import openfisca_survey_manager_location

log = logging.getLogger(__name__)


legislation_directory = os.path.join(
    openfisca_survey_manager_location,
    'openfisca_survey_manager',
    'assets',
    )


sub_levels = ['divisions', 'groupes', 'classes', 'sous_classes', 'postes']
divisions = ['0{}'.format(i) for i in range(1, 10)] + ['11', '12']


def build_coicop_level_nomenclature(level, keep_code = False, to_csv = False):
    assert level in sub_levels
    log.debug("Reading nomenclature coicop source data for level {}".format(level))
    try:
        data_frame = pd.read_csv(
            os.path.join(legislation_directory, 'nomenclature_coicop_source_by_{}.csv'.format(level)),
            sep = ';',
            header = None,
            )
    except Exception as e:
        log.info("Error when reading nomenclature coicop source data for level {}".format(level))
        raise e

    data_frame.reset_index(inplace = True, drop = True)
    data_frame.rename(columns = {0: 'code_coicop', 1: 'label_{}'.format(level[:-1])}, inplace = True)
    data_frame = data_frame.iloc[2:].copy()

    index, stop = 0, False
    for sub_level in sub_levels:
        if stop:
            continue
        if sub_level == 'divisions':
            data_frame[sub_level] = data_frame['code_coicop'].str[index:index + 2].astype(int)
            index = index + 3
        else:
            data_frame[sub_level] = data_frame['code_coicop'].str[index:index + 1].astype(int)
            index = index + 2

        if level == sub_level:
            stop = True

    if keep_code or level == 'postes':
        data_frame['code_coicop'] = data_frame['code_coicop'].str.lstrip("0")
    else:
        del data_frame['code_coicop']

    data_frame.reset_index(inplace = True, drop = True)
    if to_csv:
        data_frame.to_csv(
            os.path.join(legislation_directory, 'nomenclature_coicop_by_{}.csv'.format(level)),
            )

    return data_frame


def build_raw_coicop_nomenclature():
    """Builds raw COICOP nomenclature"""
    for index in range(len(sub_levels) - 1):
        level = sub_levels[index]
        next_level = sub_levels[index + 1]
        on = sub_levels[:index + 1]
        if index == 0:
            coicop_nomenclature = pd.merge(
                build_coicop_level_nomenclature(level), build_coicop_level_nomenclature(next_level),
                on = on, left_index = False, right_index = False)
        else:
            coicop_nomenclature = pd.merge(
                coicop_nomenclature,
                build_coicop_level_nomenclature(next_level),
                on = on,
                left_index = False,
                right_index = False,
                )

    coicop_nomenclature = coicop_nomenclature[
        ['code_coicop']
        + ['label_{}'.format(sub_level[:-1]) for sub_level in sub_levels]
        + sub_levels
        ].copy()

    return coicop_nomenclature[['label_division', 'label_groupe', 'label_classe',
       'label_sous_classe', 'label_poste', 'code_coicop']].copy()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level = logging.INFO, stream = sys.stdout)
    raw_coicop_nomenclature = build_raw_coicop_nomenclature()
    log.info(raw_coicop_nomenclature)
