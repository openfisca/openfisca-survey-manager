from openfisca_core.model_api import ETERNITY, Variable, Reform  # noqa analysis:ignore
from openfisca_country_template import CountryTaxBenefitSystem
from openfisca_country_template.entities import Person, Household


class Plugin(Reform):
    def apply(self):
        class person_weight(Variable):
            is_period_size_independent = True
            value_type = float
            entity = Person
            label = "Person weight"
            definition_period = ETERNITY

            def formula(person, period):
                return person.household('household_weight', period)

        class household_weight(Variable):
            is_period_size_independent = True
            value_type = float
            entity = Household
            label = "Household weight"
            definition_period = ETERNITY

        class household_id(Variable):
            is_period_size_independent = True
            value_type = float
            entity = Household
            label = "Household id"
            definition_period = ETERNITY

        class household_id_ind(Variable):
            is_period_size_independent = True
            value_type = float
            entity = Person
            label = "Household id of person"
            definition_period = ETERNITY

        self.add_variable(person_weight)
        self.add_variable(household_weight)
        self.add_variable(household_id)
        self.add_variable(household_id_ind)


tax_benefit_system = Plugin(CountryTaxBenefitSystem())
