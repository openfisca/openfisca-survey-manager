"""Nearest-neighbor donor (NND) hot deck matching — pure Python or R (StatMatch)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd

from openfisca_survey_manager.configuration.paths import openfisca_survey_manager_location

log = logging.getLogger(__name__)

config_files_directory = Path(openfisca_survey_manager_location)


def _normalize_list(
    x: Optional[Union[str, List[str]]],
    name: str = "variables",
) -> Optional[list[str]]:
    """Return a list of variable names from str or list."""
    if x is None:
        return None
    if isinstance(x, str):
        return [x]
    return list(x)


def _nnd_hotdeck_python(
    receiver: pd.DataFrame,
    donor: pd.DataFrame,
    matching_variables: list[str],
    donor_classes: list[str] | str | None = None,
    dist_fun: str = "Manhattan",
    random_state: int | None = None,
) -> np.ndarray:
    """
    Nearest-neighbor donor matching in pure Python (pandas + numpy).

    For each receiver row, finds the donor row that minimizes distance on
    `matching_variables`. Optionally restricts to donors in the same
    `donor_classes`. Ties are broken at random.

    Parameters
    ----------
    receiver, donor : DataFrame
        Recipient and donor datasets; must contain `matching_variables`
        (and `donor_classes` if provided). Matching variables must be numeric
        for Manhattan/Euclidean.
    matching_variables : list of str
        Column names used to compute distance.
    donor_classes : str or list of str, optional
        Columns defining donation classes; matching is done only within
        the same class. Must not contain missing values.
    dist_fun : str
        "Manhattan" (default) or "Euclidean".
    random_state : int, optional
        Seed for breaking ties.

    Returns
    -------
    mtc_ids : ndarray of int
        Shape (len(receiver), 2): (receiver_index, donor_index) for each row.
        Receiver index is 0..n_rec-1, donor index is 0..n_don-1.
    """
    rng = np.random.default_rng(random_state)
    match_vars = _normalize_list(matching_variables)
    don_class = _normalize_list(donor_classes) if donor_classes is not None else None

    for col in match_vars:
        if col not in receiver.columns or col not in donor.columns:
            raise ValueError(f"Matching variable {col!r} missing in receiver or donor")
    if don_class:
        for col in don_class:
            if col not in receiver.columns or col not in donor.columns:
                raise ValueError(f"Donor class variable {col!r} missing in receiver or donor")

    x_rec = receiver[match_vars].astype(float).values
    x_don = donor[match_vars].astype(float).values
    n_rec, n_don = len(receiver), len(donor)
    if n_don == 0:
        raise ValueError("Donor dataframe is empty")

    if dist_fun == "Manhattan":

        def dist_fn(donors: np.ndarray, rec_row: np.ndarray) -> np.ndarray:
            return np.sum(np.abs(donors - rec_row), axis=1)

    elif dist_fun == "Euclidean":

        def dist_fn(donors: np.ndarray, rec_row: np.ndarray) -> np.ndarray:
            return np.sqrt(np.sum((donors - rec_row) ** 2, axis=1))

    else:
        raise ValueError(f"dist_fun must be 'Manhattan' or 'Euclidean', got {dist_fun!r}")

    if don_class is None:
        # Global matching: for each receiver row, min distance over all donors
        donor_ix = np.zeros(n_rec, dtype=np.intp)
        for i in range(n_rec):
            d = dist_fn(x_don, x_rec[i])
            min_d = np.min(d)
            candidates = np.where(d == min_d)[0]
            donor_ix[i] = rng.choice(candidates)
        mtc_ids = np.column_stack([np.arange(n_rec), donor_ix])
        return mtc_ids

    # Within-class matching: for each group, match receiver rows to donors in same group
    rec_groups = receiver.groupby(don_class, sort=False)
    don_groups = donor.groupby(don_class, sort=False)
    donor_iloc = np.full(n_rec, -1, dtype=np.intp)
    missing_classes: list[object] = []

    for key, rec_grp in rec_groups:
        try:
            don_grp = don_groups.get_group(key)
        except KeyError:
            missing_classes.append(key)
            log.warning("No donors for class %s", key)
            continue
        x_r = rec_grp[match_vars].astype(float).values
        x_d = don_grp[match_vars].astype(float).values
        n_r, n_d = len(rec_grp), len(don_grp)
        if n_d == 0:
            continue
        # Receiver global ilocs for this group
        rec_global_ilocs = receiver.index.get_indexer(rec_grp.index)
        for j in range(n_r):
            d = dist_fn(x_d, x_r[j])
            min_d = np.min(d)
            candidates = np.where(d == min_d)[0]
            don_local = rng.choice(candidates)
            don_global_iloc = donor.index.get_loc(don_grp.index[don_local])
            donor_iloc[rec_global_ilocs[j]] = don_global_iloc

    if missing_classes:
        missing_classes_list = ", ".join(repr(class_value) for class_value in missing_classes)
        raise ValueError(
            f"No donors available for receiver donor_classes: {missing_classes_list}. "
            "All receiver classes must be present in donor when donor_classes is provided."
        )

    if np.any(donor_iloc < 0):
        raise RuntimeError("Internal error: unmatched receiver rows remain after within-class matching")

    mtc_ids = np.column_stack([np.arange(n_rec), donor_iloc])
    return mtc_ids


def _create_fused_python(
    receiver: pd.DataFrame,
    donor: pd.DataFrame,
    mtc_ids: np.ndarray,
    z_variables: list[str],
    dup_x: bool = False,
    matching_variables: list[str] | None = None,
) -> pd.DataFrame:
    """
    Build fused dataset: receiver plus z_variables from matched donors.

    mtc_ids : shape (n_receiver, 2), second column is donor position (integer).
    """
    z_vars = _normalize_list(z_variables)
    for col in z_vars:
        if col not in donor.columns:
            raise ValueError(f"z_variable {col!r} not in donor")
    fused = receiver.copy()
    don_pos = mtc_ids[:, 1]
    for col in z_vars:
        fused[col] = donor[col].iloc[don_pos].values
    if dup_x and matching_variables:
        match_vars = _normalize_list(matching_variables)
        for col in match_vars:
            if col in donor.columns:
                fused[col + "_donor"] = donor[col].iloc[don_pos].values
    return fused


def nnd_hotdeck(
    receiver: pd.DataFrame | None = None,
    donor: pd.DataFrame | None = None,
    matching_variables: str | list[str] | None = None,
    z_variables: str | list[str] | None = None,
    donor_classes: str | list[str] | None = None,
    dist_fun: str = "Manhattan",
    use_r: bool = False,
    random_state: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Nearest-neighbor donor (NND) hot deck: match each receiver row to a donor,
    then fuse z_variables from donor into receiver.

    By default uses a **pure Python** implementation (pandas + numpy).
    Set `use_r=True` to use R's StatMatch via rpy2 (same API as before).

    Parameters
    ----------
    receiver, donor : DataFrame
        Recipient and donor datasets.
    matching_variables : str or list of str
        Columns used to compute distance (must be numeric for Manhattan/Euclidean).
    z_variables : str or list of str
        Donor columns to copy into the fused dataset.
    donor_classes : str or list of str, optional
        Match only within the same class (e.g. same sex).
    dist_fun : str
        "Manhattan" (default) or "Euclidean" (pure Python); R supports more.
    use_r : bool
        If True, use R StatMatch via rpy2; otherwise use pure Python.
    random_state : int, optional
        Seed for tie-breaking (pure Python only).

    Returns
    -------
    fused_0, fused_1 : DataFrame
        fused_0: receiver + z_variables from donor (no duplicate match vars).
        fused_1: same with matching variables duplicated as _donor (if applicable).
    """
    assert receiver is not None and donor is not None
    assert matching_variables is not None and z_variables is not None
    match_vars = _normalize_list(matching_variables)
    z_vars = _normalize_list(z_variables)

    if use_r:
        return _nnd_hotdeck_rpy2(
            receiver=receiver,
            donor=donor,
            matching_variables=match_vars,
            z_variables=z_vars,
            donor_classes=donor_classes,
        )

    mtc_ids = _nnd_hotdeck_python(
        receiver,
        donor,
        match_vars,
        donor_classes=donor_classes,
        dist_fun=dist_fun,
        random_state=random_state,
    )
    fused_0 = _create_fused_python(receiver, donor, mtc_ids, z_vars, dup_x=False)
    fused_1 = _create_fused_python(receiver, donor, mtc_ids, z_vars, dup_x=True, matching_variables=match_vars)
    return fused_0, fused_1


def _nnd_hotdeck_rpy2(
    receiver: pd.DataFrame,
    donor: pd.DataFrame,
    matching_variables: list[str],
    z_variables: list[str],
    donor_classes: str | list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """R (StatMatch) implementation via rpy2; same return as nnd_hotdeck."""
    from rpy2.robjects import pandas2ri
    from rpy2.robjects.packages import importr

    pandas2ri.activate()
    stat_match = importr("StatMatch")

    if donor_classes is not None:
        don_class = _normalize_list(donor_classes)
        for col in don_class:
            if col not in receiver.columns or col not in donor.columns:
                raise ValueError(f"Donor class variable {col!r} missing")
        out_nnd = stat_match.NND_hotdeck(
            data_rec=receiver,
            data_don=donor,
            match_vars=pd.Series(matching_variables),
            don_class=pd.Series(don_class),
        )
    else:
        out_nnd = stat_match.NND_hotdeck(
            data_rec=receiver,
            data_don=donor,
            match_vars=pd.Series(matching_variables),
        )

    fused_0 = pandas2ri.ri2py(
        stat_match.create_fused(data_rec=receiver, data_don=donor, mtc_ids=out_nnd[0], z_vars=pd.Series(z_variables))
    )
    fused_1 = pandas2ri.ri2py(
        stat_match.create_fused(
            data_rec=receiver,
            data_don=donor,
            mtc_ids=out_nnd[0],
            z_vars=pd.Series(z_variables),
            dup_x=True,
            match_vars=pd.Series(matching_variables),
        )
    )
    return fused_0, fused_1


def nnd_hotdeck_using_rpy2(
    receiver: pd.DataFrame | None = None,
    donor: pd.DataFrame | None = None,
    matching_variables: str | list[str] | None = None,
    z_variables: str | list[str] | None = None,
    donor_classes: str | list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    NND hot deck via R (StatMatch). Prefer `nnd_hotdeck(..., use_r=True)`.
    """
    return nnd_hotdeck(
        receiver=receiver,
        donor=donor,
        matching_variables=matching_variables,
        z_variables=z_variables,
        donor_classes=donor_classes,
        use_r=True,
    )


def nnd_hotdeck_using_feather(
    receiver: pd.DataFrame | None = None,
    donor: pd.DataFrame | None = None,
    matching_variables: str | list[str] | None = None,
    z_variables: str | list[str] | None = None,
) -> None:
    """
    Not working
    """
    import feather

    assert receiver is not None and donor is not None
    assert matching_variables is not None

    temporary_directory_path = config_files_directory / "tmp"
    assert temporary_directory_path.exists()
    receiver_path = temporary_directory_path / "receiver.feather"
    donor_path = temporary_directory_path / "donor.feather"
    feather.write_dataframe(receiver, receiver_path)
    feather.write_dataframe(donor, donor_path)
    if isinstance(matching_variables, str):
        match_vars = f'"{matching_variables}"'
    elif len(matching_variables) == 1:
        match_vars = f'"{matching_variables[0]}"'
    else:
        match_vars = '"{}"'.format("todo")

    r_script = f"""
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
"""
    log.debug("%s", r_script)


if __name__ == "__main__":
    log.setLevel(logging.INFO)
    # Minimal example: pure Python NND hot deck (no R required)
    np.random.seed(42)
    receiver = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [10.0, 20.0, 30.0]})
    donor = pd.DataFrame({"x": [1.1, 2.2, 2.9], "y": [10.5, 19.0, 31.0], "ident": [100, 200, 300]})
    fused_0, fused_1 = nnd_hotdeck(
        receiver=receiver,
        donor=donor,
        matching_variables=["x", "y"],
        z_variables="ident",
        random_state=42,
    )
    log.info("fused_0 (receiver + z from donor):\n%s", fused_0)
    log.info("fused_1 (with _donor dup):\n%s", fused_1)
