import logging
import os
import pandas as pd


from openfisca_survey_manager import openfisca_survey_manager_location

log = logging.getLogger(__name__)


config_files_directory = os.path.join(
    openfisca_survey_manager_location)


def nnd_hotdeck_using_feather(receiver = None, donor = None, matching_variables = None, z_variables = None):
    """
    Not working
    """
    import feather

    assert receiver is not None and donor is not None
    assert matching_variables is not None

    temporary_directory_path = os.path.join(config_files_directory, 'tmp')
    assert os.path.exists(temporary_directory_path)
    receiver_path = os.path.join(temporary_directory_path, 'receiver.feather')
    donor_path = os.path.join(temporary_directory_path, 'donor.feather')
    feather.write_dataframe(receiver, receiver_path)
    feather.write_dataframe(donor, donor_path)
    if isinstance(matching_variables, str):
        match_vars = '"{}"'.format(matching_variables)
    elif len(matching_variables) == 1:
        match_vars = '"{}"'.format(matching_variables[0])
    else:
        match_vars = '"{}"'.format('todo')

    r_script = """
rm(list=ls())
gc()
devtools::install_github("wesm/feather/R")
library(feather)
library(StatMatch)

receiver <- read_feather({receiver_path})
donor <- read_feather({donor_path})
summary(receiver)
summary(donor)

# variables
receiver = as.data.frame(receiver)
donor = as.data.frame(donor)
gc()
match_vars = {match_vars}
# don_class = c("sexe")
out.nnd <- NND.hotdeck(
  data.rec = receiver, data.don = donor, match.vars = match_vars
  )

# out.nndsummary(out.nnd$mtc.ids)
# head(out.nnd$mtc.ids, 10)
# head(receiver, 10)

fused.nnd.m <- create.fused(
    data.rec = receiver, data.don = donor,
    mtc.ids = out.nnd$mtc.ids,
    z.vars = "{z_variables}"
    )
summary(fused.nnd.m)
""".format(
        receiver_path = receiver_path,
        donor_path = donor_path,
        match_vars = match_vars,
        z_variables = z_variables,
        )
    print(r_script)  # noqa analysis:ignore


def nnd_hotdeck_using_rpy2(receiver = None, donor = None, matching_variables = None,
        z_variables = None, donor_classes = None):
    from rpy2.robjects.packages import importr
    from rpy2.robjects import pandas2ri

    assert receiver is not None and donor is not None
    assert matching_variables is not None

    pandas2ri.activate()
    StatMatch = importr("StatMatch")

    if isinstance(donor_classes, str):
        assert donor_classes in receiver, 'Donor class not present in receiver'
        assert donor_classes in donor, 'Donor class not present in donor'

    try:
        if donor_classes:
            out_NND = StatMatch.NND_hotdeck(
                data_rec = receiver,
                data_don = donor,
                match_vars = pd.Series(matching_variables),
                don_class = pd.Series(donor_classes)
                )
        else:
            out_NND = StatMatch.NND_hotdeck(
                data_rec = receiver,
                data_don = donor,
                match_vars = pd.Series(matching_variables),
                # don_class = pd.Series(donor_classes)
                )
    except Exception as e:
        print(1)  # noqa analysis:ignore
        print(receiver)  # noqa analysis:ignore
        print(2)  # noqa analysis:ignore
        print(donor)  # noqa analysis:ignore
        print(3)  # noqa analysis:ignore
        print(pd.Series(matching_variables))  # noqa analysis:ignore
        print(e)  # noqa analysis:ignore

    # create synthetic data.set, without the
    # duplication of the matching variables

    fused_0 = pandas2ri.ri2py(
        StatMatch.create_fused(
            data_rec = receiver,
            data_don = donor,
            mtc_ids = out_NND[0],
            z_vars = pd.Series(z_variables)
            )
        )

    # create synthetic data.set, with the "duplication"
    # of the matching variables

    fused_1 = pandas2ri.ri2py(
        StatMatch.create_fused(
            data_rec = receiver,
            data_don = donor,
            mtc_ids = out_NND[0],
            z_vars = pd.Series(z_variables),
            dup_x = True,
            match_vars = pd.Series(matching_variables)
            )
        )

    return fused_0, fused_1


if __name__ == "__main__":
    log.setLevel(logging.INFO)

    receiver = pd.DataFrame()
    donor = pd.DataFrame()
    matching_variables = "sexe"
    z_variables = "ident"

    nnd_hotdeck_using_feather(
        receiver = receiver,
        donor = donor,
        matching_variables = matching_variables,
        z_variables = z_variables,
        )
