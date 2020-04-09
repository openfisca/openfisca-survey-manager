import numpy as np

from openfisca_survey_manager.statshelpers import bottom_share, top_share


size = 1000
x = np.ones(size) + np.random.uniform(0, .00000001, size)


def test_bottom_share():
    np.testing.assert_almost_equal(
        bottom_share(x, .4),
        .4,
        )


def test_to_share():
    np.testing.assert_almost_equal(
        top_share(x, .1),
        .1
        )
