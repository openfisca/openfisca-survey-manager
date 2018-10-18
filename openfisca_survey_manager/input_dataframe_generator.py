# -*- coding: utf-8 -*-

from __future__ import division
from builtins import range

import configparser
import logging
import os
import random


import numpy as np
import pandas as pd
import pkg_resources


from openfisca_core import periods
from openfisca_core.entities import DIVIDE
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.surveys import Survey


log = logging.getLogger(__name__)


def make_input_dataframe_by_entity(tax_benefit_system, nb_persons, nb_groups, **kwargs):
    """
        Generate a dictionnary of dataframes containing nb_persons persons spread in nb_groups groups.

        Example:

        >>> from openfisca_survey_manager.tools.input_data_generator import make_simulation
        >>> from openfisca_country_template import CountryTaxBenefitSystem
        >>> tbs = CountryTaxBenefitSystem()
        >>> data_input_by_entity = make_data_input_by_entity(tbs, 400, 100)
        # Create a simulation with 400 persons, spread among 100 households
        >>> simulation.calculate('revenu_disponible', 2017)
    """
    input_dataframe_by_entity = dict()
    person_entity = [entity for entity in tax_benefit_system.entities if entity.is_person][0]
    person_id = np.arange(nb_persons)
    input_dataframe_by_entity = dict()
    input_dataframe_by_entity[person_entity.key] = pd.DataFrame({
        person_entity.key + '_id': person_id,
        })
    input_dataframe_by_entity[person_entity.key].set_index('person_id')
    #
    adults = [0] + sorted(random.sample(range(1, nb_persons), nb_groups - 1))
    members_entity_id = np.empty(nb_persons, dtype = int)
    # A legacy role is an index that every person within an entity has.
    # For instance, the 'first_parent' has legacy role 0, the 'second_parent' 1, the first 'child' 2, the second 3, etc.
    members_legacy_role = np.empty(nb_persons, dtype = int)
    id_group = -1
    for id_person in range(nb_persons):
        if id_person in adults:
            id_group += 1
            legacy_role = 0
        else:
            legacy_role = 2 if legacy_role == 0 else legacy_role + 1
        members_legacy_role[id_person] = legacy_role
        members_entity_id[id_person] = id_group

    for entity in tax_benefit_system.entities:
        if entity.is_person:
            continue
        key = entity.key
        person_dataframe = input_dataframe_by_entity[person_entity.key]
        person_dataframe[key + '_id'] = members_entity_id
        person_dataframe[key + '_legacy_role'] = members_legacy_role
        person_dataframe[key + '_role'] = np.where(
            members_legacy_role == 0, entity.flattened_roles[0].key, entity.flattened_roles[-1].key)
        input_dataframe_by_entity[key] = pd.DataFrame({
            key + '_id': range(nb_groups)
            })
        input_dataframe_by_entity[key].set_index(key + '_id', inplace = True)

    return input_dataframe_by_entity


def random_data_generator(tax_benefit_system, nb_persons, nb_groups, variable_generators_by_period, collection):
    initial_input_dataframe_by_entity = make_input_dataframe_by_entity(tax_benefit_system, nb_persons, nb_groups)
    table_by_entity_by_period = dict()
    for period, variable_generators in variable_generators_by_period.items():
        input_dataframe_by_entity = initial_input_dataframe_by_entity.copy()
        table_by_entity_by_period[period] = table_by_entity = dict()
        for variable_generator in variable_generators:
            variable = variable_generator['variable']
            max_value = variable_generator['max_value']
            condition = variable_generator.get(None)
            randomly_init_variable(
                tax_benefit_system = tax_benefit_system,
                input_dataframe_by_entity = input_dataframe_by_entity,
                variable_name = variable,
                max_value = max_value,
                condition = condition,
                )

        for entity, input_dataframe in input_dataframe_by_entity.items():
            set_table_in_survey(input_dataframe, entity, period, collection, survey_name = 'input')
            table_by_entity[entity] = entity + '_' + str(period)

    return table_by_entity_by_period


def randomly_init_variable(tax_benefit_system, input_dataframe_by_entity, variable_name, max_value, condition = None):
    """
        Initialise a variable with random values (from 0 to max_value).
        If a condition vector is provided, only set the value of persons or groups for which condition is True.

        Exemple:

        >>> from openfisca_survey_manager.tools.input_data_generator import make_input_data_by_entity, randomly_init_variable
        >>> from openfisca_france import CountryTaxBenefitSystem
        >>> tbs = CountryTaxBenefitSystem()
        >>> input_dataframe_by_entity = make_input_dataframe_by_entity(tbs, 400, 100)  # Create an input_dataframe_by_entity with 400 persons, spread among 100 household
        >>> randomly_init_variable(tbs, input_dataframe_by_entity, 'salary', max_value = 50000, condition = "household_role == 'first_parent'")  # Randomly set a salaire_net for all persons between 0 and 50000?
        >>> input_dataframe_by_entity
        """

    variable = tax_benefit_system.variables[variable_name]
    entity = variable.entity

    if condition is None:
        condition = True
    else:
        condition = input_dataframe_by_entity[entity.key].eval(condition).values

    count = len(input_dataframe_by_entity[entity.key])
    value = (np.random.rand(count) * max_value * condition).astype(variable.dtype)
    input_dataframe_by_entity[entity.key][variable_name] = value


def set_table_in_survey(input_dataframe, entity, period, collection, survey_name, survey_label = None):
    period = periods.period(period)
    table_name = entity + '_' + str(period)
    table_label = "Input data for entity {} at period {}".format(entity, period)
    try:
        survey_collection = SurveyCollection.load(collection = collection)
    except configparser.NoOptionError:
        survey_collection = SurveyCollection(name = collection)
    except configparser.NoSectionError:  # For tests
        data_dir = os.path.join(
            pkg_resources.get_distribution('openfisca-survey-manager').location,
            'openfisca_survey_manager',
            'tests',
            'data_files',
            )
        survey_collection = SurveyCollection(
            name = collection,
            config_files_directory = data_dir,
            )

    survey = Survey(
        name = survey_name,
        label = survey_label or None,
        survey_collection = survey_collection,
        )

    if survey.hdf5_file_path is None:
        config = survey.survey_collection.config
        directory_path = config.get("data", "output_directory")
        if not os.path.isdir(directory_path):
            log.warn("{} who should be the HDF5 data directory does not exist: we create the directory".format(
                directory_path))
            os.makedirs(directory_path)
        survey.hdf5_file_path = os.path.join(directory_path, survey.name + '.h5')

    assert survey.hdf5_file_path is not None
    survey.insert_table(label = table_label, name = table_name, dataframe = input_dataframe)
    survey_collection.surveys = [
        kept_survey for kept_survey in survey_collection.surveys if kept_survey.name != survey_name
        ]
    survey_collection.surveys.append(survey)
    collections_directory = survey_collection.config.get('collections', 'collections_directory')
    assert os.path.isdir(collections_directory), """{} who should be the collections' directory does not exist.
Fix the option collections_directory in the collections section of your config file.""".format(collections_directory)
    collection_json_path = os.path.join(collections_directory, "{}.json".format(collection))
    survey_collection.dump(json_file_path = collection_json_path)


def build_input_dataframe_from_test_case(survey_scenario, test_case_scenario_kwargs, period = None,
        computed_variables = []):
    #    for axe in test_case_scenario_kwargs['axes'][0]:
    #        axe['name'] = 'salaire_imposable'

    tax_benefit_system = survey_scenario.tax_benefit_system
    simulation = tax_benefit_system.new_scenario().init_single_entity(
        **test_case_scenario_kwargs
        ).new_simulation()
    array_by_variable = dict()
    period = periods.period(period)

    def compute_variable(variable):
        if variable not in tax_benefit_system.variables:
            return
        if period.unit == periods.YEAR:
            try:
                array_by_variable[variable] = simulation.calculate(variable, period = period)
            except Exception as e:
                log.debug(e)
                try:
                    array_by_variable[variable] = simulation.calculate_add(variable, period = period)
                except Exception as e:
                    log.debug(e)
                    array_by_variable[variable] = simulation.calculate(variable, period = period.first_month)
        elif period.unit == periods.MONTH:
            try:
                array_by_variable[variable] = simulation.calculate(variable, period = period)
            except ValueError as e:
                log.debug(e)
                array_by_variable[variable] = simulation.calculate(variable, period = period.this_year) / 12

    for scenario_key, value_by_variable in test_case_scenario_kwargs.items():
        if scenario_key == 'axes':
            variables = [test_case_scenario_kwargs['axes'][0][0]['name']]

        else:
            if value_by_variable is None:  # empty parent2 for example
                continue
            if not isinstance(value_by_variable, dict):  # enfants
                continue
            variables = list(value_by_variable.keys())

        for variable in variables:
            compute_variable(variable)

    for variable in computed_variables:
        compute_variable(variable)

    for entity in tax_benefit_system.entities:
        if entity.is_person:
            continue
        array_by_variable[
            survey_scenario.id_variable_by_entity_key[entity.key]
            ] = range(test_case_scenario_kwargs['axes'][0][0]['count'])

    input_data_frame = pd.DataFrame(array_by_variable)

    for entity in tax_benefit_system.entities:
        if entity.is_person:
            continue
        input_data_frame[
            survey_scenario.role_variable_by_entity_key[entity.key]
            ] = 0



    return input_data_frame
