"""Comprehensive tests for compute_pivot_table covering all aggfuncs."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from openfisca_survey_manager.tests.test_scenario import (
    create_randomly_initialized_survey_scenario,
    setup_test_config,
)

PERIOD = "2017-01"
# Use enough groups so all 4 housing categories are very likely to appear
NB_PERSONS = 80
NB_GROUPS = 40


@pytest.fixture
def scenario(tmp_path):
    setup_test_config(tmp_path)
    return create_randomly_initialized_survey_scenario(
        nb_persons=NB_PERSONS,
        nb_groups=NB_GROUPS,
        collection=None,
        config_files_directory=tmp_path,
    )


def _df(simulation, period=PERIOD):
    """Return the household DataFrame used internally by compute_pivot_table."""
    return simulation.create_data_frame_by_entity(
        ["rent", "household_weight", "housing_occupancy_status"],
        period=period,
        index=False,
    )["household"]


# ---------------------------------------------------------------------------
# Helpers for manual aggregation
# ---------------------------------------------------------------------------


def _weighted_sum_by_cat(df, value_col, weight_col, cat_col):
    """sum(value * weight) for each category."""
    return (df.groupby(cat_col).apply(lambda g: (g[value_col] * g[weight_col]).sum())).rename(value_col)


def _weighted_mean_by_cat(df, value_col, weight_col, cat_col):
    """sum(value * weight) / sum(weight) for each category."""
    num = df.groupby(cat_col).apply(lambda g: (g[value_col] * g[weight_col]).sum())
    den = df.groupby(cat_col)[weight_col].sum()
    return (num / den).rename(value_col)


def _weight_sum_by_cat(df, weight_col, cat_col):
    """sum(weight) for each category (= count result)."""
    return df.groupby(cat_col)[weight_col].sum()


def _weighted_sum_abs_by_cat(df, value_col, weight_col, cat_col):
    """sum(|value| * weight) for each category."""
    return (df.groupby(cat_col).apply(lambda g: (g[value_col].abs() * g[weight_col]).sum())).rename(value_col)


def _min_by_cat(df, value_col, cat_col):
    """min(value) per category (no weighting)."""
    return df.groupby(cat_col)[value_col].min()


def _max_by_cat(df, value_col, cat_col):
    """max(value) per category (no weighting)."""
    return df.groupby(cat_col)[value_col].max()


# ---------------------------------------------------------------------------
# Tests: weighted aggfuncs (default weighted=True)
# ---------------------------------------------------------------------------


def test_aggfunc_sum(scenario):
    """sum aggfunc: sum(rent * weight) per housing category."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="sum",
        simulation="baseline",
    )

    expected = _weighted_sum_by_cat(df, "rent", "household_weight", "housing_occupancy_status")
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)


def test_aggfunc_mean(scenario):
    """mean aggfunc: sum(rent * weight) / sum(weight) per housing category."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="mean",
        simulation="baseline",
    )

    expected = _weighted_mean_by_cat(df, "rent", "household_weight", "housing_occupancy_status")
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)


def test_aggfunc_count(scenario):
    """count aggfunc: sum(weight) per housing category."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="count",
        simulation="baseline",
    )

    expected = _weight_sum_by_cat(df, "household_weight", "housing_occupancy_status")
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)


def test_aggfunc_sum_abs(scenario):
    """sum_abs aggfunc: sum(|rent| * weight) per housing category."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="sum_abs",
        simulation="baseline",
    )

    expected = _weighted_sum_abs_by_cat(df, "rent", "household_weight", "housing_occupancy_status")
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)


def test_aggfunc_min(scenario):
    """min aggfunc: min(rent) per housing category (no weighting)."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="min",
        simulation="baseline",
    )

    expected = _min_by_cat(df, "rent", "housing_occupancy_status")
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)


def test_aggfunc_max(scenario):
    """max aggfunc: max(rent) per housing category (no weighting)."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="max",
        simulation="baseline",
    )

    expected = _max_by_cat(df, "rent", "housing_occupancy_status")
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)


# ---------------------------------------------------------------------------
# Test: count without values (only columns/index)
# ---------------------------------------------------------------------------


def test_count_no_values(scenario):
    """count without values: weighted count per housing category."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        period=PERIOD,
        aggfunc="count",
        simulation="baseline",
    )

    expected = _weight_sum_by_cat(df, "household_weight", "housing_occupancy_status")
    # Pivot has household_weight as index when no values given
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(float(pivot[cat].values[0]), expected[cat], rtol=1e-5)


# ---------------------------------------------------------------------------
# Test: weighted=False (uniform weight=1)
# ---------------------------------------------------------------------------


def test_weighted_false_sum(scenario):
    """weighted=False sum: sum(rent) per housing category (uniform weight=1)."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="sum",
        weighted=False,
        simulation="baseline",
    )

    expected = df.groupby("housing_occupancy_status")["rent"].sum()
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)


def test_weighted_false_mean(scenario):
    """weighted=False mean: arithmetic mean of rent per housing category."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="mean",
        weighted=False,
        simulation="baseline",
    )

    expected = df.groupby("housing_occupancy_status")["rent"].mean()
    for cat in pivot.columns:
        if cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)


# ---------------------------------------------------------------------------
# Test: filter_by
# ---------------------------------------------------------------------------


def test_filter_by(scenario):
    """filter_by: only rows with rent > 0 should contribute."""
    simulation = scenario.simulations["baseline"]
    # Get raw arrays to build filtered expected values
    df = simulation.create_data_frame_by_entity(
        ["rent", "household_weight", "housing_occupancy_status", "accommodation_size"],
        period=PERIOD,
        index=False,
    )["household"]

    # Use accommodation_size > 0 as a filter (non-negative float, always >= 0)
    # We need a boolean variable; use rent > 0 but that's not an OpenFisca variable.
    # Use housing_allowance == 0 won't work well. Instead filter on accommodation_size.
    # accommodation_size is a float, so filter is: accommodation_size > 0
    # But filter_by must be a boolean variable or expression.
    # Let's use a filter expression that we can verify manually.
    # Filter by housing_occupancy_status < 2 (owner=0 or tenant=1)
    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="sum",
        filter_by="housing_occupancy_status < 2",
        simulation="baseline",
    )

    # Expected: only rows where housing_occupancy_status < 2
    mask = df["housing_occupancy_status"] < 2
    filtered_df = df[mask].copy()
    expected = _weighted_sum_by_cat(filtered_df, "rent", "household_weight", "housing_occupancy_status")

    # Only categories 0 and 1 should have non-zero values
    for cat in [0, 1]:
        if cat in pivot.columns and cat in expected.index:
            np.testing.assert_allclose(pivot.at["rent", cat], expected[cat], rtol=1e-5)

    # Categories 2 and 3 should have zero (filter zeroes out their weights)
    for cat in [2, 3]:
        if cat in pivot.columns:
            np.testing.assert_allclose(pivot.at["rent", cat], 0.0, atol=1e-5)


# ---------------------------------------------------------------------------
# Test: with index variable
# ---------------------------------------------------------------------------


def test_with_index(scenario):
    """index parameter: pivot_table with rows = housing_occupancy_status, no columns."""
    simulation = scenario.simulations["baseline"]
    df = _df(simulation)

    pivot = scenario.compute_pivot_table(
        index=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="sum",
        simulation="baseline",
    )

    # With index and no columns, pivot has housing_occupancy_status as rows
    expected = _weighted_sum_by_cat(df, "rent", "household_weight", "housing_occupancy_status")
    for cat in pivot.index:
        if cat in expected.index:
            np.testing.assert_allclose(float(pivot.loc[cat, "rent"]), expected[cat], rtol=1e-5)


# ---------------------------------------------------------------------------
# Test: result is a DataFrame with expected shape
# ---------------------------------------------------------------------------


def test_output_shape(scenario):
    """Verify output is a DataFrame with expected shape."""
    pivot = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent"],
        period=PERIOD,
        aggfunc="mean",
        simulation="baseline",
    )
    assert isinstance(pivot, pd.DataFrame)
    assert pivot.index.tolist() == ["rent"]
    # All present housing categories appear as columns (at most 4)
    assert 1 <= len(pivot.columns) <= 4


def test_multiple_values_returns_dict(scenario):
    """When multiple values are requested without concat_axis, return a dict."""
    result = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent", "accommodation_size"],
        period=PERIOD,
        aggfunc="sum",
        simulation="baseline",
    )
    assert isinstance(result, dict)
    assert "rent" in result
    assert "accommodation_size" in result


def test_multiple_values_concat_axis_0(scenario):
    """Multiple values with concat_axis=0: stacked rows."""
    result = scenario.compute_pivot_table(
        columns=["housing_occupancy_status"],
        values=["rent", "accommodation_size"],
        period=PERIOD,
        aggfunc="sum",
        concat_axis=0,
        simulation="baseline",
    )
    assert isinstance(result, pd.DataFrame)
    assert "rent" in result.index
    assert "accommodation_size" in result.index
