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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import collections
import os
import datetime
import gc
import logging

import pandas


from openfisca_survey_manager import read_sas, utils

try:
    from openfisca_survey_manager.read_spss import read_spss
except ImportError:
    read_spss = None


log = logging.getLogger(__name__)


class Table(object):
    """
    An object to describe a table from survey data
    """
    label = None
    name = None
    source_format = None
    survey = None
    variables = None

    def __init__(self, survey = None, name = None, label = None, source_format = None, variables = None,
                 **kwargs):
        assert name is not None, "A table should have a name"
        self.name = name
        if label is not None:
            self.label = label
        if variables is not None:
            self.variables = variables
        self.informations = kwargs

        if source_format is not None:
            self.source_format = source_format

        from .surveys import Survey  # Keep it here to avoid infinite recursion
        assert isinstance(survey, Survey), 'survey is of type {} and not {}'.format(type(survey), Survey)
        self.survey = survey
        if not survey.tables:
            survey.tables = collections.OrderedDict()

        survey.tables[name] = collections.OrderedDict(
            source_format = source_format,
            variables = variables
            )

    def _check_and_log(self, data_file_path):
        if not os.path.isfile(data_file_path):
            raise Exception("file_path {} do not exists".format(data_file_path))
        log.info("Inserting table {} from file {} in HDF file {} at point {}".format(
            self.name,
            data_file_path,
            self.survey.hdf5_file_path,
            self.name,
            ))

    def _save(self, data_frame = None):
        assert data_frame is not None

        table = self
        hdf5_file_path = table.survey.hdf5_file_path

        variables = table.variables
        log.info("Inserting table {} in HDF file {}".format(table.name, hdf5_file_path))
        store_path = table.name
        if variables:
            stored_variables = list(set(variables).intersection(set(data_frame.columns)))
            log.info('The folloging variables are stored: {}'.format(stored_variables))
            if set(stored_variables) != set(variables):
                log.info('variables wanted by the user that were not available: {}'.format(
                    list(set(variables) - set(stored_variables))
                    ))
            data_frame = data_frame[stored_variables].copy()
        try:
            data_frame.to_hdf(hdf5_file_path, store_path, append = False)
        except (TypeError, NotImplementedError):
            dtypes = data_frame.dtypes
            converted_dtypes = dtypes.isin(['mixed', 'unicode', 'category'])
            log.info("The following types are converted to strings \n {}".format(dtypes[converted_dtypes]))
            for column in dtypes[converted_dtypes].index:
                try:
                    data_frame[column] = data_frame[column].astype(str).copy()
                except UnicodeEncodeError:
                    continue
            data_frame.to_hdf(hdf5_file_path, store_path, append = False)
        gc.collect()

    def fill_hdf(self, **kwargs):
        source_format = self.source_format

        reader_by_source_format = dict(
            # Rdata = pandas.rpy.common.load_data,
            sas = read_sas.read_sas,
            spss = read_spss,
            stata = pandas.read_stata,
            )
        start_table_time = datetime.datetime.now()
        reader = reader_by_source_format[source_format]
        data_file = kwargs.pop("data_file")
        overwrite = kwargs.pop('overwrite')
        clean = kwargs.pop("clean")

        # if source_format == 'stata':
        #     kwargs[]
        if not overwrite:
            store = pandas.HDFStore(self.survey.hdf5_file_path)
            if self.name in store:
                log.info('Exiting without overwriting {} in '.format(self.name, self.survey.hdf5_file_path))
        else:
            self._check_and_log(data_file)
            try:
                try:
                    data_frame = reader(data_file, **kwargs)
                except ValueError as e:
                    log.info('Error while reading {}'.format(data_file))
                    raise e
                gc.collect()
                if clean:
                    utils.clean_data_frame(data_frame)
                self._save(data_frame = data_frame)
                log.info("File {} has been processed in {}".format(
                    data_file, datetime.datetime.now() - start_table_time))
            except ValueError as e:
                raise e
                log.info('Skipping file {} because of following error \n {}'.format(data_file, e))

    def save_data_frame(self, data_frame, **kwargs):
        data_frame.to_hdf(self.survey.hdf5_file_path, self.name, append = False, **kwargs)
