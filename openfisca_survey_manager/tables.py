

import collections
import os
import datetime
import gc
import logging

import pandas


from openfisca_survey_manager import read_sas

try:
    from openfisca_survey_manager.read_spss import read_spss
except ImportError:
    read_spss = None


log = logging.getLogger(__name__)


class Table(object):
    """A table of a survey."""
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
            log.info("Type problem(s) when creating {} in {}".format(store_path, hdf5_file_path))
            dtypes = data_frame.dtypes
            # Checking for strings
            converted_dtypes = dtypes.isin(['mixed', 'unicode'])
            if converted_dtypes.any():
                log.info("The following types are converted to strings \n {}".format(dtypes[converted_dtypes]))
                # Conversion to strings
                for column in dtypes[converted_dtypes].index:
                    data_frame[column] = data_frame[column].copy().astype(str)

            # Checking for remaining categories
            dtypes = data_frame.dtypes
            converted_dtypes = dtypes.isin(['category'])
            if not converted_dtypes.empty:  # With category table format is needed
                log.info("The following types are added as category using the table format\n {}".format(dtypes[converted_dtypes]))
                data_frame.to_hdf(hdf5_file_path, store_path, append = False, format = 'table')

        gc.collect()

    def fill_hdf(self, **kwargs):
        source_format = self.source_format

        reader_by_source_format = dict(
            # Rdata = pandas.rpy.common.load_data,
            csv = pandas.read_csv,
            sas = read_sas.read_sas,
            spss = read_spss,
            stata = pandas.read_stata,
            )
        start_table_time = datetime.datetime.now()
        data_file = kwargs.pop("data_file")
        overwrite = kwargs.pop('overwrite')
        clean = kwargs.pop("clean")

        # if source_format == 'stata':
        #     kwargs[]
        if not overwrite:
            store = pandas.HDFStore(self.survey.hdf5_file_path)
            if self.name in store:
                log.info(
                    'Exiting without overwriting {} in {}'.format(
                        self.name, self.survey.hdf5_file_path))
        else:
            self._check_and_log(data_file)
            try:
                try:
                    reader = reader_by_source_format[source_format]
                    if source_format == 'csv':
                        data_frame = reader(data_file, sep = None, **kwargs)
                    else:
                        data_frame = reader(data_file, **kwargs)
                except ValueError as e:
                    log.info('Error while reading {}'.format(data_file))
                    raise e
                gc.collect()
                if clean:
                    clean_data_frame(data_frame)
                self._save(data_frame = data_frame)
                log.info("File {} has been processed in {}".format(
                    data_file, datetime.datetime.now() - start_table_time))
            except ValueError as e:
                log.info('Skipping file {} because of following error \n {}'.format(data_file, e))
                raise e

    def save_data_frame(self, data_frame, **kwargs):
        data_frame.to_hdf(self.survey.hdf5_file_path, self.name, append = False, **kwargs)


def clean_data_frame(data_frame):
    data_frame.columns = data_frame.columns.str.lower()
    object_column_names = list(data_frame.select_dtypes(include=["object"]).columns)
    log.info(
        "The following variables are to be cleaned or left as strings : \n {}".format(object_column_names)
        )
    for column_name in object_column_names:
        # print(data_frame[column_name].value_counts())
        if data_frame[column_name].isnull().all():  #
            log.info("Drop empty column {}".format(column_name))
            data_frame.drop(column_name, axis = 1, inplace = True)
            continue

        values = list(data_frame[column_name].value_counts().keys())
        empty_string_present = "" in values
        if empty_string_present:
            values.remove("")
        all_digits = all([value.strip().isdigit() for value in values])
        no_zero = all([value != 0 for value in values])
        if all_digits and no_zero:
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
            try:
                data_frame[column_name] = data_frame[column_name].astype("int")
            except OverflowError:
                log.info(
                    'OverflowError when converting {} to int. Keeping as {}'.format(
                        column_name, data_frame[column_name].dtype)
                    )
