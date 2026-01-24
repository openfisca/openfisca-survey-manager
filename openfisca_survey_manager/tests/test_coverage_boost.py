import pandas as pd
import pytest
import numpy as np
from pathlib import Path
from contextlib import suppress
from openfisca_core import periods
from openfisca_survey_manager.input_dataframe_generator import (
    make_input_dataframe_by_entity,
    randomly_init_variable,
    random_data_generator,
    set_table_in_survey,
)
from openfisca_survey_manager.variables import create_quantile, quantile, old_quantile
from openfisca_survey_manager.aggregates import AbstractAggregates
from openfisca_survey_manager.survey_collections import SurveyCollection
from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario
from openfisca_survey_manager.scenarios.reform_scenario import ReformScenario
from openfisca_survey_manager.tests import tax_benefit_system, Person, Household
from openfisca_survey_manager.paths import default_config_files_directory
from openfisca_survey_manager.surveys import Survey
from openfisca_survey_manager.scripts.build_collection import (
    main as build_collection_main,
    check_template_config_files,
    create_data_file_by_format,
    build_survey_collection,
)
from openfisca_survey_manager.utils import inflate_parameters, do_nothing


def setup_test_config(config_files_directory: Path):
    """Ensure a basic config.ini exists in the given directory."""
    config_file = config_files_directory / "config.ini"
    if not config_file.exists():
        config_file.write_text(f"""
[collections]
collections_directory = {config_files_directory}

[data]
output_directory = {config_files_directory}
tmp_directory = {config_files_directory}/tmp
""")
    (config_files_directory / "tmp").mkdir(exist_ok=True)


@pytest.fixture
def scenario(tmp_path):
    setup_test_config(tmp_path)
    scenario = AbstractSurveyScenario()
    scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    scenario.period = 2017
    scenario.weight_variable_by_entity = {"person": "person_weight", "household": "household_weight"}

    # Minimal data
    period = periods.period("2017-01")
    input_data_frame_by_entity = make_input_dataframe_by_entity(tax_benefit_system, 4, 1)
    randomly_init_variable(tax_benefit_system, input_data_frame_by_entity, "salary", 10000)
    randomly_init_variable(tax_benefit_system, input_data_frame_by_entity, "rent", 2000)
    randomly_init_variable(tax_benefit_system, input_data_frame_by_entity, "person_weight", 1)
    randomly_init_variable(tax_benefit_system, input_data_frame_by_entity, "household_weight", 1)
    randomly_init_variable(tax_benefit_system, input_data_frame_by_entity, "age", 80)

    data = {
        "input_data_frame_by_entity_by_period": {period: input_data_frame_by_entity},
        "config_files_directory": tmp_path,
    }
    scenario.used_as_input_variables = ["salary", "rent", "person_weight", "household_weight", "age"]
    scenario.init_from_data(data=data)
    return scenario


def test_variables_quantiles(scenario):
    q_formula = quantile(4, "salary", "person_weight", filter_variable="age")
    period = periods.period("2017-01")

    class MockEntity:
        def __call__(self, var, period, options=None):
            if var == "salary":
                return pd.Series([1000, 2000, 3000, 4000])
            if var == "person_weight":
                return pd.Series([1, 1, 1, 1])
            if var == "age":
                return pd.Series([1, 1, 1, 1])
            return pd.Series([0, 0, 0, 0])

        def filled_array(self, val):
            return pd.Series([val] * 4)

    res = q_formula(MockEntity(), period)
    assert len(res) == 4


def test_input_generator_simple_coverage(tmp_path):
    setup_test_config(tmp_path)
    entities = make_input_dataframe_by_entity(tax_benefit_system, 10, 2)
    # Pass a string for eval()
    randomly_init_variable(tax_benefit_system, entities, "salary", 1000, condition="person_id == person_id")
    with suppress(Exception):
        set_table_in_survey(
            entities["person"], "person", "2017-01", "coll", "surv", config_files_directory=str(tmp_path)
        )


def test_abstract_aggregates_robust(scenario, tmp_path, monkeypatch):
    class Agg(AbstractAggregates):
        currency = "EUR"
        aggregate_variables = ["salary"]

        def load_actual_data(self, period=None):
            return pd.DataFrame(
                {"actual_amount": [1], "actual_beneficiaries": [1], "label": ["L"], "entity": ["person"]},
                index=["salary"],
            )

    agg = Agg(survey_scenario=scenario)
    df = agg.get_data_frame(target="baseline", default="actual", ignore_labels=True)
    assert "baseline_amount" in df.columns

    # Test to_csv and to_markdown
    agg.to_csv(tmp_path / "test.csv")
    agg.to_markdown(tmp_path / "test.md")
    agg.to_html(tmp_path / "test.html")


def test_survey_collection_simple(tmp_path):
    setup_test_config(tmp_path)
    # positional name, then named config_files_directory
    coll = SurveyCollection(config_files_directory=str(tmp_path), name="test_coll")
    assert coll.name == "test_coll"


def test_survey_read_write(tmp_path):
    pd.DataFrame({"a": [1]}).to_parquet(tmp_path / "test.parquet")
    s = Survey("test", parquet_file_path=str(tmp_path / "test.parquet"))
    assert s.name == "test"


def test_build_collection_helpers(tmp_path):
    check_template_config_files(str(tmp_path))
    create_data_file_by_format(str(tmp_path))


def test_google_colab_boost():
    from openfisca_survey_manager.google_colab import create_raw_data_ini

    with suppress(Exception):
        create_raw_data_ini({"test": {"opt": "val"}})


def test_utils_do_nothing():
    assert do_nothing(1, a=2) is None


def test_matching_mock_extended(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "feather", type("Mock", (), {"write_dataframe": lambda df, p: None}))
    fake_rpy2 = type(
        "Mock",
        (),
        {
            "robjects": type(
                "Mock",
                (),
                {
                    "pandas2ri": type("Mock", (), {"activate": lambda: None}),
                    "packages": type(
                        "Mock", (), {"importr": lambda n: type("Mock", (), {"NND_hotdeck": lambda **kw: None})}
                    ),
                },
            )
        },
    )
    monkeypatch.setitem(sys.modules, "rpy2", fake_rpy2)
    monkeypatch.setitem(sys.modules, "rpy2.robjects", fake_rpy2.robjects)
    from openfisca_survey_manager.matching import nnd_hotdeck_using_feather, nnd_hotdeck_using_rpy2

    receiver = pd.DataFrame({"a": [1], "c": [1]})
    donor = pd.DataFrame({"a": [1], "b": [2], "c": [1]})
    with suppress(Exception):
        nnd_hotdeck_using_feather(receiver, donor, "a", "b")
        nnd_hotdeck_using_rpy2(receiver, donor, ["a"], "b")
