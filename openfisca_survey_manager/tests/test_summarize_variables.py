import logging

import pytest

from openfisca_survey_manager.tests.test_scenario import create_randomly_initialized_survey_scenario

log = logging.getLogger(__name__)


def test_summarize_variable():
    survey_scenario = create_randomly_initialized_survey_scenario()
    survey_scenario.summarize_variable(variable="rent", force_compute=True)
    survey_scenario.summarize_variable(variable="housing_occupancy_status", force_compute=True)


def test_summarize_variable_log_output(caplog):
    """Assert that summarize_variable logs the same kind of output as the former doctest.

    The doctest used to check stdout; we now send that output to the logging system.
    This test captures logs and verifies the expected content is present.
    """
    with caplog.at_level(logging.INFO, logger="openfisca_survey_manager.simulations"):
        survey_scenario = create_randomly_initialized_survey_scenario(collection=None)
        survey_scenario.summarize_variable(variable="housing_occupancy_status", force_compute=True)

    messages = [r.message for r in caplog.records]
    text = " ".join(messages)
    assert "housing_occupancy_status" in text
    assert "periods" in text and "cells" in text
    assert "Details" in text
    # Enum variable: categories (owner, tenant, etc.) appear in the summary
    assert "owner" in text or "tenant" in text or "free_lodger" in text or "homeless" in text

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="openfisca_survey_manager.simulations"):
        survey_scenario.summarize_variable(variable="rent", force_compute=True)

    messages = [r.message for r in caplog.records]
    text = " ".join(messages)
    assert "rent" in text
    assert "Details" in text
    assert "mean" in text

    survey_scenario.tax_benefit_systems["baseline"].neutralize_variable("age")
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="openfisca_survey_manager.simulations"):
        survey_scenario.summarize_variable(variable="age")

    messages = [r.message for r in caplog.records]
    text = " ".join(messages)
    assert "age" in text
    assert "neutralized" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
