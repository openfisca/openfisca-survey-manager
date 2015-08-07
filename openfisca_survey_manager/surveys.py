#! /usr/bin/env python
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
#

import collections
import os
import re

import logging
import pandas
import yaml


from .tables import Table


ident_re = re.compile(u"(?i)ident\d{2,4}$")

log = logging.getLogger(__name__)


source_format_by_extension = dict(
    sas7bdat = "sas",
    dta = 'stata',
    Rdata = 'Rdata',  # TODO: badly named
    spss = 'sav'
    )


class Survey(object):
    """
    An object to describe survey data
    """
    hdf5_file_path = None
    informations = dict()
    label = None
    name = None
    tables = collections.OrderedDict()
    tables_index = dict()
    survey_collection = None

    def __init__(self, name = None, label = None, hdf5_file_path = None,
                 survey_collection = None, **kwargs):
        assert name is not None, "A survey should have a name"
        self.name = name
        self.tables = dict()

        if label is not None:
            self.label = label

        if hdf5_file_path is not None:
            self.hdf5_file_path = hdf5_file_path

        if survey_collection is not None:
            self.survey_collection = survey_collection

        self.informations = kwargs

    def __repr__(self):
        header = """{} : survey data {}
Contains the following tables : \n""".format(self.name, self.label)
        tables = yaml.safe_dump(
            self.tables.keys(),
            default_flow_style = False)
        informations = yaml.safe_dump(self.informations, default_flow_style = False)
        return header + tables + informations

    @classmethod
    def create_from_json(cls, survey_json):
        self = cls(
            name = survey_json.get('name'),
            label = survey_json.get('label'),
            hdf5_file_path = survey_json.get('hdf5_file_path'),
            **survey_json.get('informations', dict())
            )
        self.tables = survey_json.get('tables')
        return self

    def dump(self):
        assert self.survey_collection is not None
        self.survey_collection.dump()

    def fill_hdf(self, source_format = None, tables = None, overwrite = True):
        assert self.survey_collection is not None
        assert isinstance(overwrite, bool) or isinstance(overwrite, list)
        survey = self
        if survey.hdf5_file_path is None:
            config = survey.survey_collection.config
            directory_path = config.get("data", "output_directory")
            assert os.path.isdir(directory_path), """{} who should be the HDF5 data directory does not exist.
Fix the option output_directory in the collections section of your config file.""".format(directory_path)
            survey.hdf5_file_path = os.path.join(directory_path, survey.name + '.h5')
        if source_format is None:
            source_formats = ['stata', 'sas', 'spss', 'Rdata']
        else:
            source_formats = [source_format]

        for source_format in source_formats:
            files = "{}_files".format(source_format)
            for data_file in survey.informations.get(files, []):
                path_name, extension = os.path.splitext(data_file)
                name = os.path.basename(path_name)
                if tables is None or name in tables:
                    table = Table(
                        label = name,
                        name = name,
                        source_format = source_format_by_extension[extension[1:]],
                        survey = survey,
                        )
                    table.fill_hdf(
                        data_file = data_file,
                        clean = True,
                        overwrite = overwrite if isinstance(overwrite, bool) else table.name in overwrite,
                        )
        self.dump()

    def find_tables(self, variable = None, tables = None, rename_ident = True):
        container_tables = []

        assert variable is not None

        if tables is None:
            tables = self.tables
        tables_index = self.tables_index
        for table in tables:
            if table not in tables_index.keys():
                tables_index[table] = self.get_columns(table)
            if variable in tables_index[table]:
                container_tables.append(table)
        return container_tables

    def get_columns(self, table = None, rename_ident = True):
        assert table is not None
        store = pandas.HDFStore(self.hdf5_file_path)
        if table in store:
            log.info("Building columns index for table {}".format(table))
            data_frame = store[table]
            if rename_ident is True:
                for column_name in data_frame:
                    if ident_re.match(column_name) is not None:
                        data_frame.rename(columns = {column_name: "ident"}, inplace = True)
                        log.info("{} column have been replaced by ident".format(column_name))
                        break
            return list(data_frame.columns)
        else:
            print 'table {} was not found in {}'.format(table, store.filename)
            return list()

    def get_value(self, variable = None, table = None):
        """
        Get value

        Parameters
        ----------
        variable : string
                  name of the variable
        table : string, default None
                name of the table hosting the variable
        Returns
        -------
        df : DataFrame, default None
             A DataFrame containing the variable
        """
        assert variable is not None, "A variable is needed"
        if table not in self.tables:
            log.error("Table {} is not found in survey tables".format(table))
        df = self.get_values([variable], table)
        return df

    def get_values(self, variables = None, table = None, lowercase = True, rename_ident = True):
        """
        Get values

        Parameters
        ----------
        variables : list of strings, default None
                  list of variables names, if None return the whole table
        table : string, default None
                name of the table hosting the variables
        lowercase : boolean, deflault True
                    put variables of the table into lowercase
        rename_ident :  boolean, deflault True
                        rename variables ident+yr (e.g. ident08) into ident
        Returns
        -------
        df : DataFrame, default None
             A DataFrame containing the variables
        """
        store = pandas.HDFStore(self.hdf5_file_path)
        try:
            df = store[table]
        except KeyError:
            log.error('No table {} in the file {}'.format(table, self.hdf5_file_path))

        if lowercase is True:
            columns = dict((column_name, column_name.lower()) for column_name in df)
            df.rename(columns = columns, inplace = True)

        if rename_ident is True:
            for column_name in df:
                if ident_re.match(column_name) is not None:
                    df.rename(columns = {column_name: "ident"}, inplace = True)
                    log.info("{} column have been replaced by ident".format(column_name))
                    break

        if variables is None:
            return df
        else:
            diff = set(variables) - set(df.columns)
            if diff:
                raise Exception("The following variable(s) {} are missing".format(diff))
            variables = list(set(variables).intersection(df.columns))
            df = df[variables]
            return df

    def insert_table(self, name = None, **kwargs):
        """
        Insert a table in the Survey object
        """

        data_frame = kwargs.pop('data_frame', None)
        if data_frame is not None:
            assert isinstance(data_frame, pandas.DataFrame)

        if data_frame is not None:
            table = Table(label = name, name = name, survey = self)
            assert table.survey.hdf5_file_path is not None
            table.save_data_frame(data_frame)

        if name not in self.tables:
            self.tables[name] = dict()
        for key, val in kwargs.iteritems():
            self.tables[name][key] = val

    def to_json(self):
        self_json = collections.OrderedDict((
            ))
        self_json['hdf5_file_path'] = self.hdf5_file_path
        self_json['label'] = self.label
        self_json['name'] = self.name
        self_json['tables'] = self.tables
        self_json['informations'] = collections.OrderedDict(sorted(self.informations.iteritems()))
        return self_json
