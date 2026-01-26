"""Tests for the survey scenario functionality in OpenFisca Survey Manager."""

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from openfisca_core import periods
from openfisca_core.tools import assert_near

from openfisca_survey_manager.input_dataframe_generator import (
    make_input_dataframe_by_entity,
    random_data_generator,
    randomly_init_variable,
)
from openfisca_survey_manager.paths import (
    default_config_files_directory,
)
from openfisca_survey_manager.scenarios.abstract_scenario import AbstractSurveyScenario
from openfisca_survey_manager.scenarios.reform_scenario import ReformScenario
from openfisca_survey_manager.tests import tax_benefit_system

log = logging.getLogger(__name__)


def setup_test_config(config_files_directory: Path):
    """Ensure a basic config.ini exists in the given directory."""
    config_file = config_files_directory / "config.ini"
    if not config_file.exists():
        config_file.write_text(f"""
[collections]
collections_directory = {config_files_directory}

[data]
output_directory = {config_files_directory}
tmp_directory = {config_files_directory / "tmp"}
""")
    (config_files_directory / "tmp").mkdir(exist_ok=True)


def create_randomly_initialized_survey_scenario(
    nb_persons: int = 10,
    nb_groups: int = 5,
    salary_max_value: float = 50000,
    rent_max_value: float = 1000,
    collection: Optional[str] = "test_random_generator",
    use_marginal_tax_rate: bool = False,
    reform: Optional[Callable] = None,
    config_files_directory: Optional[Path] = None,
) -> AbstractSurveyScenario:
    """
    Create a randomly initialized survey scenario.

    Args:
        nb_persons (int): Number of persons
        nb_groups (int): Number of groups
        salary_max_value (float): Maximum salary value
        rent_max_value (float): Maximum rent value
        collection (Optional[str]): Collection name
        use_marginal_tax_rate (bool): Use marginal tax rate
        reform (Optional[Callable]): Reform function
        config_files_directory (Optional[Path]): Directory where configuration files are stored.

    Returns:
        AbstractSurveyScenario: Initialized survey scenario
    """
    if config_files_directory is not None:
        setup_test_config(config_files_directory)

    if collection is not None:
        return create_randomly_initialized_survey_scenario_from_table(
            nb_persons,
            nb_groups,
            salary_max_value,
            rent_max_value,
            collection,
            use_marginal_tax_rate,
            reform=reform,
            config_files_directory=config_files_directory,
        )
    else:
        return create_randomly_initialized_survey_scenario_from_data_frame(
            nb_persons,
            nb_groups,
            salary_max_value,
            rent_max_value,
            use_marginal_tax_rate,
            reform=reform,
            config_files_directory=config_files_directory,
        )


def create_randomly_initialized_survey_scenario_from_table(
    nb_persons: int,
    nb_groups: int,
    salary_max_value: float,
    rent_max_value: float,
    collection: str,
    use_marginal_tax_rate: bool,
    reform: Optional[Callable] = None,
    config_files_directory: Optional[Path] = None,
) -> AbstractSurveyScenario:
    """
    Create a randomly initialized survey scenario from a table.
    """
    variable_generators_by_period = {
        periods.period("2017-01"): [
            {
                "variable": "salary",
                "max_value": salary_max_value,
            },
            {
                "variable": "rent",
                "max_value": rent_max_value,
            },
            {
                "variable": "household_weight",
                "max_value": 100,
            },
        ],
        periods.period("2018-01"): [
            {
                "variable": "salary",
                "max_value": salary_max_value,
            },
            {
                "variable": "rent",
                "max_value": rent_max_value,
            },
        ],
    }
    table_by_entity_by_period = random_data_generator(
        tax_benefit_system,
        nb_persons,
        nb_groups,
        variable_generators_by_period,
        collection,
        config_files_directory=config_files_directory,
    )
    if reform is None:
        survey_scenario = AbstractSurveyScenario()
        survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    else:
        survey_scenario = ReformScenario()
        survey_scenario.set_tax_benefit_systems(
            {
                "reform": reform(tax_benefit_system),
                "baseline": tax_benefit_system,
            }
        )

    survey_scenario.used_as_input_variables = [
        "salary",
        "rent",
        "housing_occupancy_status",
        "household_weight",
    ]
    survey_scenario.period = 2017
    survey_scenario.collection = collection
    data = {
        "survey": "input",
        "input_data_table_by_entity_by_period": table_by_entity_by_period,
        "config_files_directory": config_files_directory or default_config_files_directory,
    }
    if use_marginal_tax_rate:
        survey_scenario.varying_variable = "salary"

    survey_scenario.weight_variable_by_entity = {
        "person": "person_weight",
        "household": "household_weight",
    }
    survey_scenario.init_from_data(data=data, use_marginal_tax_rate=use_marginal_tax_rate)
    return survey_scenario


def create_randomly_initialized_survey_scenario_from_data_frame(
    nb_persons: int,
    nb_groups: int,
    salary_max_value: float,
    rent_max_value: float,
    use_marginal_tax_rate: bool = False,
    reform: Optional[Callable] = None,
    config_files_directory: Optional[Path] = None,
) -> AbstractSurveyScenario:
    """
    Create a randomly initialized survey scenario from a data frame.
    """
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(
        nb_persons, nb_groups, salary_max_value, rent_max_value
    )
    for entity in input_data_frame_by_entity:
        if entity == "person":
            input_data_frame_by_entity[entity]["household_id_ind"] = input_data_frame_by_entity[entity]["household_id"]
        if entity == "household":
            input_data_frame_by_entity[entity]["household_id"] = input_data_frame_by_entity[entity].index

    weight_variable_by_entity = {
        "person": "person_weight",
        "household": "household_weight",
    }
    if reform is None:
        survey_scenario = AbstractSurveyScenario()
        survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    else:
        survey_scenario = ReformScenario()
        survey_scenario.set_tax_benefit_systems(
            {
                "reform": reform(tax_benefit_system),
                "baseline": tax_benefit_system,
            }
        )
    survey_scenario.period = 2017
    survey_scenario.used_as_input_variables = [
        "salary",
        "rent",
        "household_weight",
        "household_id",
        "household_id_ind",
    ]
    period = periods.period("2017-01")

    data = {
        "input_data_frame_by_entity_by_period": {period: input_data_frame_by_entity},
        "config_files_directory": config_files_directory or default_config_files_directory,
    }
    survey_scenario.set_weight_variable_by_entity(weight_variable_by_entity)
    survey_scenario.init_from_data(data=data, use_marginal_tax_rate=use_marginal_tax_rate)
    return survey_scenario


def generate_input_input_dataframe_by_entity(
    nb_persons: int, nb_groups: int, salary_max_value: float, rent_max_value: float
) -> dict[str, Any]:
    """Generate input dataframe by entity."""
    input_dataframe_by_entity = make_input_dataframe_by_entity(tax_benefit_system, nb_persons, nb_groups)
    randomly_init_variable(
        tax_benefit_system,
        input_dataframe_by_entity,
        "salary",
        max_value=salary_max_value,
        condition="household_role == 'first_parent'",
    )
    randomly_init_variable(tax_benefit_system, input_dataframe_by_entity, "rent", max_value=rent_max_value)
    randomly_init_variable(
        tax_benefit_system,
        input_dataframe_by_entity,
        "household_weight",
        max_value=100,
    )
    randomly_init_variable(
        tax_benefit_system,
        input_dataframe_by_entity,
        "housing_occupancy_status",
        max_value=4,
    )
    return input_dataframe_by_entity


def test_input_dataframe_generator() -> None:
    """Test the input dataframe generator function."""
    input_dataframe_by_entity = generate_input_input_dataframe_by_entity(10, 5, 50000, 1000)
    assert (input_dataframe_by_entity["person"]["household_role"] == "first_parent").sum() == 5
    assert (input_dataframe_by_entity["household"]["rent"] > 0).all()


def test_init_from_data(tmp_path) -> None:
    """Test the initialization of data in the survey scenario."""
    setup_test_config(tmp_path)
    survey_scenario = AbstractSurveyScenario()
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(10, 5, 50000, 1000)
    period = periods.period("2017-01")
    data_in = {
        "input_data_frame_by_entity_by_period": {period: input_data_frame_by_entity},
        "config_files_directory": tmp_path,
    }
    survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    survey_scenario.used_as_input_variables = ["salary", "rent", "household_weight"]
    survey_scenario.period = 2017
    survey_scenario.init_from_data(data=data_in)
    assert len(survey_scenario.simulations) == 1


def test_survey_scenario_input_dataframe_import(tmp_path) -> None:
    """Test the import of input dataframes into a survey scenario."""
    setup_test_config(tmp_path)
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(10, 5, 50000, 1000)
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    survey_scenario.period = 2017
    survey_scenario.used_as_input_variables = ["salary", "rent"]
    period = periods.period("2017-01")
    data = {
        "input_data_frame_by_entity_by_period": {period: input_data_frame_by_entity},
        "config_files_directory": tmp_path,
    }
    survey_scenario.init_from_data(data=data)
    simulation = survey_scenario.simulations["baseline"]
    assert (simulation.calculate("salary", period) == input_data_frame_by_entity["person"]["salary"]).all()


def test_survey_scenario_input_dataframe_import_scrambled_ids(tmp_path) -> None:
    """Test survey scenario input dataframe import with scrambled IDs."""
    setup_test_config(tmp_path)
    input_data_frame_by_entity = generate_input_input_dataframe_by_entity(10, 5, 50000, 1000)
    input_data_frame_by_entity["person"]["household_id"] = 4 - input_data_frame_by_entity["person"]["household_id"]
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    survey_scenario.period = 2017
    survey_scenario.used_as_input_variables = ["salary", "rent"]
    period = periods.period("2017-01")
    data = {
        "input_data_frame_by_entity_by_period": {period: input_data_frame_by_entity},
        "config_files_directory": tmp_path,
    }
    survey_scenario.init_from_data(data=data)
    simulation = survey_scenario.simulations["baseline"]
    assert (simulation.calculate("salary", period) == input_data_frame_by_entity["person"]["salary"]).all()


def test_dump_survey_scenario(tmp_path: Any) -> None:
    """Test the dump and restore functionality of survey scenarios."""
    setup_test_config(tmp_path)
    directory = tmp_path / "dump"
    survey_scenario = create_randomly_initialized_survey_scenario(config_files_directory=tmp_path)
    survey_scenario.dump_simulations(directory=str(directory))
    period = "2017-01"
    df = survey_scenario.create_data_frame_by_entity(variables=["salary", "rent"], period=period)
    household = df["household"]
    del survey_scenario
    survey_scenario = AbstractSurveyScenario()
    survey_scenario.set_tax_benefit_systems({"baseline": tax_benefit_system})
    survey_scenario.used_as_input_variables = ["salary", "rent"]
    survey_scenario.period = 2017
    survey_scenario.restore_simulations(directory=str(directory))
    df2 = survey_scenario.create_data_frame_by_entity(variables=["salary", "rent"], period="2017-01")
    assert (df2["household"] == household).all().all()


def test_inflate(tmp_path) -> None:
    """Test the inflate method."""
    setup_test_config(tmp_path)
    survey_scenario = create_randomly_initialized_survey_scenario(collection=None, config_files_directory=tmp_path)
    period = "2017-01"
    inflator = 2.42
    inflator_by_variable = {"rent": inflator}
    rent_before = survey_scenario.compute_aggregate("rent", period=period)
    survey_scenario.inflate(inflator_by_variable=inflator_by_variable, period=period)
    rent_after = survey_scenario.compute_aggregate("rent", period=period)
    assert_near(rent_after, inflator * rent_before, relative_error_margin=1e-6)


def test_compute_pivot_table(tmp_path) -> None:
    """Test compute_pivot_table."""
    setup_test_config(tmp_path)
    survey_scenario = create_randomly_initialized_survey_scenario(collection=None, config_files_directory=tmp_path)
    period = "2017-01"
    pivot_table = survey_scenario.compute_pivot_table(
        columns=["age"], values=["salary"], period=period, simulation="baseline"
    )
    assert pivot_table.index == "salary"


def test_compute_quantile(tmp_path) -> None:
    """Test compute_quantiles."""
    setup_test_config(tmp_path)
    survey_scenario = create_randomly_initialized_survey_scenario(config_files_directory=tmp_path)
    period = "2017-01"
    quintiles = survey_scenario.compute_quantiles(
        variable="salary",
        nquantiles=5,
        period=period,
        weighted=False,
        simulation="baseline",
    )
    assert len(quintiles) == 6


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    test_compute_quantile()
