from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario

survey_scenario = create_randomly_initialized_survey_scenario(collection = None)

survey_scenario.tax_benefit_system.neutralize_variable('age')
survey_scenario.tax_benefit_system.neutralize_variable('rent')

survey_scenario.summarize_variable(variable = "age", force_compute = True)
survey_scenario.summarize_variable(variable = "salary")

