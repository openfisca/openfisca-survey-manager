

import numpy as np
import pandas as pd


from openfisca_core.model_api import Variable, YEAR
from openfisca_core.entities import build_entity
from openfisca_core.taxbenefitsystems import TaxBenefitSystem
from openfisca_survey_manager.scenarios import AbstractSurveyScenario
from openfisca_survey_manager.statshelpers import mark_weighted_percentiles
from openfisca_survey_manager.variables import quantile


Individu = build_entity(
    key = "individu",
    plural = "individus",
    label = 'Individu',
    is_person = True,
    )

entities = [Individu]


class salaire(Variable):
    value_type = float
    entity = Individu
    label = "Salaire"
    definition_period = YEAR


class decile_salaire_from_quantile(Variable):
    entity = Individu
    value_type = int
    label = "Décile de salaire nouveau calcul"
    definition_period = YEAR
    formula = quantile(q = 10, variable = 'salaire')


class decile_salaire(Variable):
    value_type = int
    entity = Individu
    label = "Décile de salaire"
    definition_period = YEAR

    def formula(individu, period):
        salaire = individu('salaire', period)
        labels = np.arange(1, 11)
        weights = 1.0 * np.ones(shape = len(salaire))
        decile, _ = mark_weighted_percentiles(
            salaire,  # + np.random.uniform(size = len(salaire)) - 0.5,
            labels,
            weights,
            method = 2,
            return_quantiles = True,
            )
        return decile


class QuantileTestTaxBenefitSystem(TaxBenefitSystem):
    """PPDLand tax and benefit system"""
    CURRENCY = ""

    def __init__(self):
        super(QuantileTestTaxBenefitSystem, self).__init__(entities)
        for variable in [
                decile_salaire_from_quantile,
                decile_salaire,
                salaire,
                ]:
            self.add_variable(variable)


class QuantileTestSurveyScenario(AbstractSurveyScenario):
    def __init__(self, input_data_frame = None, tax_benefit_system = None,
            baseline_tax_benefit_system = None, year = None):
        super(QuantileTestSurveyScenario, self).__init__()
        assert input_data_frame is not None
        assert year is not None
        self.year = year
        if tax_benefit_system is None:
            tax_benefit_system = QuantileTestTaxBenefitSystem()
        self.set_tax_benefit_systems(
            tax_benefit_system = tax_benefit_system,
            baseline_tax_benefit_system = baseline_tax_benefit_system
            )
        self.used_as_input_variables = list(
            set(tax_benefit_system.variables.keys()).intersection(
                set(input_data_frame.columns)
                ))
        data = {
            'input_data_frame': input_data_frame
            }
        self.init_from_data(data = data)


def create_input_dataframe(size = 9):
    """
    Create input dataframe with variable salaire and pension_retraite
    """
    np.random.seed(216)
    household_weight = 1.0
    number_of_indididual = size
    size = int(number_of_indididual / household_weight)
    salaire = np.linspace(0, 100, size)
    return pd.DataFrame({
        'salaire': salaire,
        })


def test_quantile():
    size = 10000
    input_data_frame = create_input_dataframe(size = size)
    survey_scenario = QuantileTestSurveyScenario(
        input_data_frame = input_data_frame,
        tax_benefit_system = QuantileTestTaxBenefitSystem(),
        year = 2017,
        )
    data = np.linspace(1, 11 - 1e-5, size)
    target = np.floor(data)
    result = survey_scenario.calculate_variable(
        variable = 'decile_salaire_from_quantile', period = '2017'
        )
    assert all(
        (result == target) + (abs(result - target + 1) < .001)  # Finite size problem handling
        ), "{} != {}, \n{} , \n{},".format(
            result[result != target],
            target[result != target],
            data[result != target],
            abs(result - target + 1)[result != target],
            )

    # No reason that method coincides so close to the quantiles thresholds
    # assert all(survey_scenario.calculate_variable(
    #     variable = 'decile_salaire_from_quantile', period = '2017'
    #     ) == survey_scenario.calculate_variable(
    #         variable = 'decile_salaire', period = '2017'
    #         )
    #     )


if __name__ == '__main__':
    test_quantile()
