import logging


from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario


log = logging.getLogger(__name__)


def test_create_data_frame_by_entity():
    survey_scenario = create_randomly_initialized_survey_scenario()
    period = '2017-01'
    df_by_entity = survey_scenario.create_data_frame_by_entity(
        variables = ['salary', 'rent'],
        period = period,
        )
    salary = survey_scenario.calculate_variable('salary', period = period)
    rent = survey_scenario.calculate_variable('rent', period = period)
    for entity, df in df_by_entity.items():
        assert not df.empty, f"{entity} dataframe is empty"
    assert (df_by_entity['person']['salary'] == salary).all().all()
    assert (df_by_entity['household']['rent'] == rent).all().all()


def test_create_data_frame_by_entity_with_index():
    survey_scenario = create_randomly_initialized_survey_scenario()
    period = '2017-01'
    data_frame_by_entity = survey_scenario.create_data_frame_by_entity(
        variables = ['salary', 'rent', "person_id"],
        period = period,
        index = True
        )
    for entity, input_dataframe in data_frame_by_entity.items():
        print(f"{entity} for {period}")  # noqa T201
        print(input_dataframe.columns)  # noqa T201
        if entity == "person":
            assert "person_id" in input_dataframe.columns.to_list()
        if entity == "household":
            assert "household_id" in input_dataframe.columns.to_list()
