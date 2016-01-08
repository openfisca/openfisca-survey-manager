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
from openfisca_survey_manager.scripts.build_collection import add_survey_to_collection


def test_add_survey_to_collection():
    name = 'fake'
    survey_name = 'fake_survey'
    survey_collection = SurveyCollection(name = name)

    data_dir = os.path.join(
        pkg_resources.get_distribution('openfisca-survey-manager').location,
        'openfisca_survey_manager',
        'tests',
        'data_files',
        )
#    saved_fake_survey_hdf5_file_path = os.path.join(data_dir, 'fake.hdf5')
    saved_fake_survey_file_path = os.path.join(data_dir, 'help.sas7bdat')
    add_survey_to_collection(survey_name = survey_name,
                             survey_collection = survey_collection,
                             sas_files = [saved_fake_survey_file_path],
                             stata_files = [])
    ordered_dict = survey_collection.to_json()
#    print ordered_dict
    assert ordered_dict['surveys'].keys() == [survey_name]


if __name__ == '__main__':
    test_add_survey_to_collection()
