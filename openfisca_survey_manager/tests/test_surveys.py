# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import pkg_resources


from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey


def test_survey():
    name = 'fake'
    data_dir = os.path.join(
        pkg_resources.get_distribution('openfisca-survey-manager').location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )

    survey_collection = SurveyCollection(
        name = name,
        config_files_directory = data_dir,
        json_file_path = os.path.join(data_dir, 'fake.json')
        )

    saved_fake_survey_hdf5_file_path = os.path.join(data_dir, 'fake.hdf5')
    saved_fake_survey_file_path = os.path.join(data_dir, 'help.sas7bdat')
    survey = Survey(
        hdf5_file_path = saved_fake_survey_hdf5_file_path,
        name = 'fake_survey',
        sas_files = [saved_fake_survey_file_path],
        survey_collection = survey_collection,
        )
    survey.insert_table(name = 'help')
    survey.fill_hdf(source_format = 'sas')
    print survey.tables
#    survey.dump(saved_fake_survey_file_path)
#    survey_bis = Survey.load(saved_fake_survey_file_path)
#    assert survey.to_json() == survey_bis.to_json()


if __name__ == '__main__':
    test_survey()
