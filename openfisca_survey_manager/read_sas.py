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


import logging

try:
    from sas7bdat import SAS7BDAT
except ImportError:
    SAS7BDAT = None

log = logging.getLogger(__name__)


def read_sas(sas_file_path, clean = False):

    assert SAS7BDAT is not None
    data_frame = SAS7BDAT(sas_file_path).to_data_frame()
    if clean:
        try:
            clean_data_frame(data_frame)
        except AttributeError:
            pass
    return data_frame


def clean_data_frame(data_frame):
    object_column_names = list(data_frame.select_dtypes(include=["object"]).columns)
    log.info(
        "The following variables are to be cleaned or left as strings : \n {}".format(object_column_names)
        )
    for column_name in object_column_names:

        if data_frame[column_name].isnull().all():  # drop empty columns
            data_frame.drop(column_name, axis = 1, inplace = True)
            continue

        values = list(data_frame[column_name].value_counts().keys())
        empty_string_present = "" in values
        if empty_string_present:
            values.remove("")
        all_digits = all([value.isdigit() for value in values])
        no_zero = all([value != 0 for value in values])
        if all_digits:
            if no_zero:
                log.info(
                    "Replacing empty string with zero for variable {}".format(column_name)
                    )
                data_frame.replace(
                    to_replace = {
                        column_name: {"": 0},
                        },
                    inplace = True,
                    )

            log.info(
                "Converting string variable {} to integer".format(column_name)
                )
            data_frame[column_name] = data_frame[column_name].astype("int")
    return data_frame