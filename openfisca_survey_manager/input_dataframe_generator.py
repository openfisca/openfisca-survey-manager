# -*- coding: utf-8 -*-

from __future__ import division


import numpy as np
import pandas as pd
import random


from openfisca_core import periods


def make_input_dataframe_by_entity(tax_benefit_system, nb_persons, nb_groups, **kwargs):
    """
        Generate a dictionnary of dataframes containing nb_persons persons spread in nb_groups groups.

        Exemple:

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
    adults = [0] + sorted(random.sample(xrange(1, nb_persons), nb_groups - 1))
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

from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.tables import Table


def set_table_in_survey(input_dataframe, entity, period, collection, survey):
    period = periods.period(period)
    name = entity + '_' + str(period)
    label = "Input data for entity {} at period {}".format(entity, period)
    survey_collection = SurveyCollection.load(collection = collection)
    survey = survey_collection.get_survey(survey)

    survey.insert_table(label = label, name = name, dataframe = input_dataframe)


def random_data_generator(tax_benefit_system, nb_persons, nb_groups, variable_generators_by_period, collection):
    initial_input_dataframe_by_entity = make_input_dataframe_by_entity(tax_benefit_system, nb_persons, nb_groups)
    for period, variable_generators in variable_generators_by_period.iteritems():
        for variable_generator in variable_generators:
            variable = variable_generator['variable']
            max_value = variable_generator['max_value']
            condition = variable_generator.get(None)
            input_dataframe_by_entity = initial_input_dataframe_by_entity.copy()
            randomly_init_variable(
                tax_benefit_system = tax_benefit_system,
                input_dataframe_by_entity = input_dataframe_by_entity,
                variable_name = variable,
                max_value = max_value,
                condition = condition,
                )
        survey = 'input'
        for entity, input_dataframe in input_dataframe_by_entity.iteritems():
            set_table_in_survey(input_dataframe, entity, period, collection, survey)