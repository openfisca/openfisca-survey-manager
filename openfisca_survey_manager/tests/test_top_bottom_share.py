import numpy as np
import pytest

from openfisca_survey_manager.policy.statshelpers import _weighted_quantile, bottom_share, top_share

size = 1000
x = np.ones(size) + np.random.uniform(0, 0.00000001, size)


def test_bottom_share():
    np.testing.assert_almost_equal(
        bottom_share(x, 0.4),
        0.4,
    )


def test_to_share():
    np.testing.assert_almost_equal(top_share(x, 0.1), 0.1)


def test_bottom_and_top_share_handle_tied_boundary_values():
    values = np.array([1.0, 1.0, 1.0, 2.0])

    assert bottom_share(values, 0.5) == pytest.approx(0.4)
    assert top_share(values, 0.5) == pytest.approx(0.6)


def test_weighted_quantile_rejects_degenerate_inputs():
    with pytest.raises(ValueError, match="same length"):
        _weighted_quantile(np.array([1.0, 2.0]), np.array([1.0]), 0.5)

    with pytest.raises(ValueError, match="positive value"):
        _weighted_quantile(np.array([1.0, 2.0]), np.array([0.0, 0.0]), 0.5)
