import logging
import unittest

from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario

log = logging.getLogger(__name__)


class TestCreateDataFrameByEntity(unittest.TestCase):
    def test_create_data_frame_by_entity(self):
        survey_scenario = create_randomly_initialized_survey_scenario()
        period = '2017-01'
        df_by_entity = survey_scenario.create_data_frame_by_entity(variables = ['salary', 'rent'], period = period)
        salary = survey_scenario.calculate_variable('salary', period = period)
        rent = survey_scenario.calculate_variable('rent', period = period)
        for entity, df in df_by_entity.items():
            assert not df.empty, "{} dataframe is empty".format(entity)
        assert (df_by_entity['person']['salary'] == salary).all().all()
        assert (df_by_entity['household']['rent'] == rent).all().all()

    def test_create_data_frame_by_entity_with_index(self):
        survey_scenario = create_randomly_initialized_survey_scenario()
        period = '2017-01'
        data_frame_by_entity = survey_scenario.create_data_frame_by_entity(
            variables = ['salary', 'rent', "person_id", "household_id"],
            period = period,
            index = True
            )
        for entity, input_dataframe in data_frame_by_entity.items():
            print(f"{entity} for {period}")
            print(input_dataframe.columns)
            if entity == "person":
                self.assertIn("person_id", input_dataframe.columns.to_list())
            if entity == "household":
                self.assertIn("household_id", input_dataframe.columns.to_list())
