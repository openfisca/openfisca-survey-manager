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
try:
    import pandas.rpy.common as com
except ImportError:
    com = None
try:
    import rpy2.rpy_classic as rpy
except ImportError:
    rpy = None


from openfisca_survey_manager.read_sas import read_sas
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
    variables = list()

    def __init__(self, survey = None, name = None, label = None, source_format = source_format, variables = None,
                 **kwargs):
        assert name is not None, "A table should have a name"
        self.name = name
        if label is not None:
            self.label = label
        if variables is not None:
            self.variables = variables
        self.informations = kwargs

        from .surveys import Survey
        assert isinstance(survey, Survey)
        self.survey = survey
        if not survey.tables:
            survey.tables = collections.OrderedDict()
        survey.tables[name] = collections.OrderedDict(
            source_format = source_format,
            variables = variables
            )

    def _save(self, data_frame = None):
        assert data_frame is not None
        table = self
        hdf5_file_path = table.survey.hdf5_file_path
        variables = table.variables
        log.info("Inserting table {} in HDF file {}".format(table.name, hdf5_file_path))
        store_path = table.name

        if variables is not None:
            stored_variables = list(set(variables).intersection(set(data_frame.columns)))
            log.info('The folloging variables are stored: {}'.format(stored_variables))
            if set(stored_variables) != set(variables):
                log.info('variables wanted by the user that were not available: {}'.format(
                    list(set(variables) - set(stored_variables))
                    ))
            data_frame = data_frame[stored_variables].copy()
        try:
            data_frame.to_hdf(hdf5_file_path, store_path, format = 'table', append = False)
        except TypeError:
            types = data_frame.apply(lambda x: pandas.lib.infer_dtype(x.values))
            log.info("The following types are converted to strings \n {}".format(types[types == 'unicode']))
            for column in types[types == 'unicode'].index:
                data_frame[column] = data_frame[column].astype(str)
            data_frame.to_hdf(hdf5_file_path, store_path)
        gc.collect()

    def fill_hdf(self, **kwargs):
        source_format = self.source_format
        if source_format == "Rdata":
            self.fill_hdf_from_Rdata(**kwargs)
        if source_format == "sas":
            self.fill_hdf_from_sas(**kwargs)
        if source_format == "spss":
            self.fill_hdf_from_spss(**kwargs)
        if source_format == "stata":
            self.fill_hdf_from_stata(**kwargs)

    def fill_hdf_from_Rdata(self):
        rpy.set_default_mode(rpy.NO_CONVERSION)
        Rdata_table = self.informations["Rdata_table"]
        Rdata_file = self.informations["Rdata_file"]
        self._check_and_log(Rdata_file)
        rpy.r.load(Rdata_file)
        data_frame = pandas.rpy.common.load_data(Rdata_table)
        self._save(data_frame = data_frame)

    def fill_hdf_from_sas(self, **kwargs):
        start_table_time = datetime.datetime.now()
        sas_file = kwargs["data_file"]
        self.data_file = sas_file
        clean = kwargs.get("clean")
        self._check_and_log(sas_file)
        data_frame = read_sas.read_sas(sas_file, clean = clean)
        self._save(data_frame = data_frame)
        gc.collect()
        log.info("{} have been processed in {}".format(sas_file, datetime.datetime.now() - start_table_time))

    def fill_hdf_from_spss(self):
        spss_file = self.informations["spss_file"]  # .sav file name
        self._check_and_log(spss_file)
        data_frame = read_spss(spss_file)
        self._save(data_frame = data_frame)
        gc.collect()

    def fill_hdf_from_stata(self, table):
        stata_file = self.informations["stata_file"]
        self._check_and_log(stata_file)
        log.info("Reading from {}".format(stata_file))
        data_frame = pandas.read_stata(stata_file)
        self._save(data_frame = data_frame)
        gc.collect()

    def _check_and_log(self, data_file_path):
        if not os.path.isfile(data_file_path):
            raise Exception("file_path {} do not exists".format(data_file_path))
        log.info("Inserting table {} from file {} in HDF file {} at point {}".format(
            self.name,
            data_file_path,
            self.survey.hdf5_file_path,
            self.name,
            )
        )
