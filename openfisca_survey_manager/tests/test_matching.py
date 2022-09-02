
import pandas as pd

from openfisca_survey_manager.matching import nnd_hotdeck_using_rpy2

try:
    import rpy2
    from rpy2.robjects import r
    from rpy2.robjects.packages import importr
    from rpy2.robjects import pandas2ri
except ImportError:
    rpy2 = None


def test_reproduction():
    if rpy2 is None:
        return

    # Reproducing examples from StatMatch documenation
    # https://cran.r-project.org/web/packages/StatMatch/StatMatch.pdf

    r.data('iris')

    pandas2ri.activate()
    # or explcitly do:
    # iris = pandas2ri.ri2py(r['iris'])

    iris = r['iris']

    # lab = list([1:15, 51:65, 101:115)
    # recipient data.frame
    iris_rec = pd.concat([
        iris.loc[1:15],
        iris.loc[51:65],
        iris.loc[101:115],
        ])
    iris_rec.columns
    del iris_rec["Petal.Width"]

    # donor data.frame
    iris_don = pd.concat([
        iris.loc[16:50],
        iris.loc[66:100],
        iris.loc[116:150],
        ])
    del iris_rec["Petal.Length"]

    # Now iris.rec and iris.don have the variables
    # "Sepal.Length", "Sepal.Width" and "Species"
    # in common.
    # "Petal.Length" is available only in iris.rec
    # "Petal.Width" is available only in iris.don
    # find the closest donors using NND hot deck;
    # distances are computed on "Sepal.Length" and "Sepal.Width"

    StatMatch = importr("StatMatch")

    out_NND = StatMatch.NND_hotdeck(
        data_rec = iris_rec, data_don=iris_don,
        match_vars = pd.Series(["Sepal.Length", "Sepal.Width"]),
        don_class = "Species"
        )

    # create synthetic data.set, without the
    # duplication of the matching variables
    fused_0 = pandas2ri.ri2py(
        StatMatch.create_fused(
            data_rec = iris_rec,
            data_don = iris_don,
            mtc_ids = out_NND[0],
            z_vars = "Petal.Width"
            )
        )

    # create synthetic data.set, with the "duplication"
    # of the matching variables
    fused_1 = pandas2ri.ri2py(
        StatMatch.create_fused(
            data_rec = iris_rec,
            data_don = iris_don,
            mtc_ids = out_NND[0],
            z_vars = "Petal.Width",
            dup_x = True,
            match_vars = pd.Series(["Sepal.Length", "Sepal.Width"])
            )
        )
    del fused_0, fused_1


def test_nnd_hotdeck_using_rpy2():
    if rpy2 is None:
        print('rpy2 is absent: skipping test')  # noqa analysis:ignore
        return

    r.data('iris')

    pandas2ri.activate()
    # or explcitly do:
    # iris = pandas2ri.ri2py(r['iris'])

    iris = r['iris']

    # lab = list([1:15, 51:65, 101:115)
    # recipient data.frame
    iris_rec = pd.concat([
        iris.loc[1:15],
        iris.loc[51:65],
        iris.loc[101:115],
        ])
    iris_rec.columns
    del iris_rec["Petal.Width"]

    # donor data.frame
    iris_don = pd.concat([
        iris.loc[16:50],
        iris.loc[66:100],
        iris.loc[116:150],
        ])
    del iris_rec["Petal.Length"]

    # Now iris.rec and iris.don have the variables
    # "Sepal.Length", "Sepal.Width" and "Species"
    # in common.
    # "Petal.Length" is available only in iris.rec
    # "Petal.Width" is available only in iris.don

    # find the closest donors using NND hot deck;
    # distances are computed on "Sepal.Length" and "Sepal.Width"

    x, y = nnd_hotdeck_using_rpy2(
        receiver = iris_rec,
        donor = iris_don,
        donor_classes = 'Species',
        z_variables = "Petal.Width",
        matching_variables = ["Sepal.Length", "Sepal.Width"]
        )
