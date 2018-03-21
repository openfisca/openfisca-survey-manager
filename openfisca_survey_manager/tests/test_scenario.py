# -*- coding: utf-8 -*-

from __future__ import division


import numpy as np
import pandas as pd
import random


from openfisca_country_template import CountryTaxBenefitSystem

tax_benefit_system = CountryTaxBenefitSystem()


def make_input_dataframe_by_entity(tax_benefit_system, nb_persons, nb_groups, **kwargs):
    """
        Generate a dictionnary of dataframes containing nb_persons persons spread in nb_groups groups.

        Exemple:

        >>> from openfisca_survey_manager.tools.input_data_generator import make_simulation
        >>> from openfisca_france import CountryTaxBenefitSystem
        >>> tbs = CountryTaxBenefitSystem()
        >>> data_input_by_entity = make_data_input_by_entity(tbs, 400, 100)
        # Create a simulation with 400 persons, spread among 100 households
        >>> simulation.calculate('revenu_disponible', 2017)
    """
    make_input_dataframe_by_entity = dict()

    person_entity = [entity for entity in tax_benefit_system.entities if entity.is_person][0]
    person_id = np.arange(nb_persons)
    input_dataframe_by_entity = dict()
    input_dataframe_by_entity[person_entity.key] = pd.DataFrame(
        dict(
            person_id = person_id,
            )
        )
    #
    adults = [0] + sorted(random.sample(xrange(1, nb_persons), nb_groups - 1))
    members_entity_id = np.empty(nb_persons, dtype = int)
    # A legacy role is an index that every person within an entity has. For instance, the 'demandeur' has legacy role 0, the 'conjoint' 1, the first 'child' 2, the second 3, etc.
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
        if not entity.is_person:
            key = entity.key
            person_dataframe = input_dataframe_by_entity[person_entity.key]
            person_dataframe[key + '_id'] = members_entity_id
            person_dataframe[key + '_legacy_role'] = members_legacy_role
            person_dataframe[key + '_role'] = np.where(members_legacy_role == 0, entity.flattened_roles[0], entity.flattened_roles[-1])
            input_dataframe_by_entity[key] = pd.DataFrame({
                key + '_id': range(nb_groups)
                })

    return input_dataframe_by_entity


def randomly_init_variable(input_dataframe_by_entity, variable_name, period, max_value, condition = None):
    """
        Initialise a variable with random values (from 0 to max_value) for the given period.
        If a condition vector is provided, only set the value of persons or groups for which condition is True.

        Exemple:

        >>> from openfisca_survey_manager.tools.input_data_generator import make_input_data_by_entity, randomly_init_variable
        >>> from openfisca_france import CountryTaxBenefitSystem
        >>> tbs = CountryTaxBenefitSystem()
        >>> simulation = make_simulation(tbs, 400, 100)  # Create a simulation with 400 persons, spread among 100 families
        >>> randomly_init_variable(simulation, 'salaire_net', 2017, max_value = 50000, condition = simulation.persons.has_role(simulation.famille.DEMANDEUR))  # Randomly set a salaire_net for all persons between 0 and 50000?
        >>> simulation.calculate('revenu_disponible', 2017)
        """
    if condition is None:
        condition = True
    variable = simulation.tax_benefit_system.get_variable(variable_name)
    entity = simulation.get_variable_entity(variable_name)
    value = (np.random.rand(entity.count) * max_value * condition).astype(variable.dtype)
    entity.get_holder(variable_name).set_input(make_period(period), value)


input_dataframe_by_entity = make_input_dataframe_by_entity(tax_benefit_system, 10, 5)
print input_dataframe_by_entity