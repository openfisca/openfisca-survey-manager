# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
from pathlib import Path

from pandas.testing import assert_frame_equal

from openfisca_survey_manager.paths import openfisca_survey_manager_location
from openfisca_survey_manager.read_sas import read_sas


def test():
    sas_file_path = (
        Path(openfisca_survey_manager_location) / "openfisca_survey_manager" / "tests" / "data_files" / "help.sas7bdat"
    )
    data_frame = read_sas(sas_file_path, clean=False)
    data_frame_clean = read_sas(sas_file_path, clean=True)

    assert_frame_equal(data_frame, data_frame_clean)

    assert len(data_frame.columns) == 88
    assert len(data_frame) == 453
