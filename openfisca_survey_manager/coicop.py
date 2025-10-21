import logging
import os
from pathlib import Path

import pandas as pd

from openfisca_survey_manager.paths import openfisca_survey_manager_location

log = logging.getLogger(__name__)


legislation_directory = Path(
    openfisca_survey_manager_location,
    "openfisca_survey_manager",
    "assets",
)
legislation_directory = Path(
    openfisca_survey_manager_location,
    "openfisca_survey_manager",
    "assets",
)


sub_levels = ["divisions", "groupes", "classes", "sous_classes", "postes"]
divisions = [f"0{i}" for i in range(1, 10)] + ["11", "12"]


def build_coicop_level_nomenclature(level, year=2016, keep_code=False, to_csv=False):
    assert level in sub_levels
    log.debug(
        f"Reading nomenclature coicop {year} source data for level {level}"
    )
    try:
        if year == 1998:
            data_frame = pd.read_csv(
                os.path.join(
                    legislation_directory,
                    f"COICOP/1998/nomenclature_coicop1998_source_by_{level}.csv",
                ),
                sep=";",
                header=None,
            )
        if year == 2016:
            data_frame = pd.read_excel(
                os.path.join(
                    legislation_directory,
                    f"COICOP/2016/nomenclature_coicop2016_source_by_{level}.xls",
                ),
                header=None,
            )

    except Exception:
        log.info(
            f"Error when reading nomenclature coicop source data for level {level}"
        )
        raise

    data_frame = data_frame.reset_index()
    data_frame = data_frame.rename(
        columns={0: "code_coicop", 1: f"label_{level[:-1]}"}
    )
    data_frame = data_frame.iloc[2:].copy()
    if year == 2016:
        data_frame["code_coicop"] = data_frame["code_coicop"].apply(lambda x: x[1:])

    index, stop = 0, False
    for sub_level in sub_levels:
        if stop:
            continue
        if sub_level == "divisions":
            data_frame[sub_level] = (
                data_frame["code_coicop"].str[index : index + 2].astype(int)
            )
            index = index + 3
        else:
            data_frame[sub_level] = (
                data_frame["code_coicop"].str[index : index + 1].astype(int)
            )
            index = index + 2

        if level == sub_level:
            stop = True

    if keep_code or level == "postes":
        data_frame["code_coicop"] = data_frame["code_coicop"].str.lstrip("0")
    else:
        del data_frame["code_coicop"]

    data_frame = data_frame.reset_index(drop=True)
    if to_csv:
        data_frame.to_csv(
            os.path.join(
                legislation_directory,
                f"nomenclature_coicop{year}_by_{level}.csv",
            ),
        )

    return data_frame


def build_raw_coicop_nomenclature(year=2016):
    """Builds raw COICOP nomenclature from ecoicop levels."""
    coicop_nomenclature = None

    for index in range(len(sub_levels) - 1):
        level = sub_levels[index]
        next_level = sub_levels[index + 1]
        on = sub_levels[: index + 1]

        df_left = (
            coicop_nomenclature
            if coicop_nomenclature is not None
            else build_coicop_level_nomenclature(level, year)
        )
        df_right = build_coicop_level_nomenclature(next_level, year)

        # Drop any residual 'index' columns to avoid merge conflicts
        for df in (df_left, df_right):
            if "index" in df.columns:
                df = df.drop(columns=["index"])  # noqa: PLW2901

        coicop_nomenclature = df_left.merge(
            df_right,
            on=on,
            how="inner",
            validate="one_to_many",  # safety check
        )

    # Reorder and select relevant columns
    coicop_nomenclature = coicop_nomenclature[
        ["code_coicop"]
        + [f"label_{sub_level[:-1]}" for sub_level in sub_levels]
        + sub_levels
    ].copy()

    return coicop_nomenclature[
        [
            "label_division",
            "label_groupe",
            "label_classe",
            "label_sous_classe",
            "label_poste",
            "code_coicop",
        ]
    ].copy()


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    raw_coicop_nomenclature = build_raw_coicop_nomenclature()
    log.info(raw_coicop_nomenclature)
