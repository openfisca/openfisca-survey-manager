# -*- coding: utf-8 -*-


import logging
import os
from pandas import DataFrame, concat


log = logging.getLogger(__name__)


def clean_data_frame(data_frame):
    object_column_names = list(data_frame.select_dtypes(include=["object"]).columns)
    log.info(
        "The following variables are to be cleaned or left as strings : \n {}".format(object_column_names)
        )
    for column_name in object_column_names:
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


def dump_simulation_results_data_frame(survey_scenario, collection = None):
    assert collection is not None
    year = survey_scenario.year
    data_frame_by_entity = get_calculated_data_frame_by_entity(survey_scenario)
    openfisca_survey_collection = SurveyCollection.load(collection = "openfisca")
    output_data_directory = openfisca_survey_collection.config.get('data', 'output_directory')
    survey_name = "openfisca_data_{}".format(year)
    for entity, data_frame in data_frame_by_entity.iteritems():
        table = entity
        hdf5_file_path = os.path.join(
            os.path.dirname(output_data_directory),
            "{}{}".format(survey_name, ".h5"),
            )
        survey = Survey(
            name = survey_name,
            hdf5_file_path = hdf5_file_path,
            )
        survey.insert_table(name = table)
        survey.fill_hdf(table, data_frame)
        openfisca_survey_collection.surveys[survey_name] = survey
        openfisca_survey_collection.dump(collection = "openfisca")


def get_data_frame(columns_name, survey_scenario, load_first = False, collection = None):
    year = survey_scenario.year
    if survey_scenario.simulation is None:
        survey_scenario.new_simulation()
    simulation = survey_scenario.simulation
    if load_first:
        assert collection is not None
        entities = [simulation.tax_benefit_system.variables[column_name].entity for column_name in columns_name]
        assert len(set(entities)) == 1
        # entity_symbol = entities[0]
        for entity_key, entity in simulation.entities.iteritems():
            if columns_name[0] in entity.variables:
                break
        openfisca_survey_collection = SurveyCollection.load(collection = collection)
        survey_name = "openfisca_data_{}".format(year)
        survey = openfisca_survey_collection.surveys[survey_name]
        table = entity_key
        data_frame = survey.get_values(variables = columns_name, table = table)
    else:
        data_frame = DataFrame(dict([(column_name, simulation.calculate(column_name)) for column_name in columns_name]))
    return data_frame

