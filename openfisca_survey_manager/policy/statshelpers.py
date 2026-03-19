"""Statistical helpers (Gini, Lorenz, weighted percentiles, etc.)."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
import weightedcalcs as wc
from numpy import argsort, asarray, cumsum, linspace, ones, repeat, zeros
from numpy import logical_and as and_

log = logging.getLogger(__name__)


def _coerce_weighted_inputs(
    data: np.ndarray | pd.Series,
    weights: Optional[np.ndarray | pd.Series] = None,
) -> tuple[np.ndarray, np.ndarray]:
    data = asarray(data, dtype=float)
    if data.ndim != 1:
        raise ValueError("data must be one-dimensional")
    if len(data) == 0:
        raise ValueError("data must not be empty")

    if weights is None:
        weights = ones(len(data))
    weights = asarray(weights, dtype=float)
    if weights.ndim != 1:
        raise ValueError("weights must be one-dimensional")
    if len(data) != len(weights):
        raise ValueError("data and weights must have the same length")
    if np.any(weights < 0):
        raise ValueError("weights must be non-negative")
    if weights.sum() <= 0:
        raise ValueError("weights must sum to a positive value")

    return data, weights


def _weighted_quantile(data: np.ndarray, weights: np.ndarray, q: float) -> float:
    """Compute the q-th weighted quantile of 1D data.

    Uses the midpoint formula (compatible with the former weightedcalcs/wquantiles behaviour).

    Args:
        data: 1D array of values.
        weights: 1D array of non-negative weights (same length as data).
        q: Quantile in [0, 1].

    Returns:
        float: Interpolated quantile value.
    """
    if not 0 <= q <= 1:
        raise ValueError("q must be between 0 and 1")

    data, weights = _coerce_weighted_inputs(data, weights)
    sort_idx = argsort(data)
    sorted_data = data[sort_idx]
    sorted_weights = weights[sort_idx]
    cum_weights = cumsum(sorted_weights)
    # Midpoint-based p_vals: each observation's "representative percentile"
    p_vals = (cum_weights - 0.5 * sorted_weights) / cum_weights[-1]
    return float(np.interp(q, p_vals, sorted_data))


def _weighted_bottom_share(
    values: np.ndarray | pd.Series,
    rank_from_bottom: float,
    weights: Optional[np.ndarray | pd.Series] = None,
) -> float:
    if not 0 <= rank_from_bottom <= 1:
        raise ValueError("rank_from_bottom must be between 0 and 1")

    values, weights = _coerce_weighted_inputs(values, weights)
    total = (values * weights).sum()
    if total == 0:
        raise ValueError("weighted sum of values must not be zero")
    if rank_from_bottom == 0:
        return 0.0
    if rank_from_bottom == 1:
        return 1.0

    sort_idx = argsort(values)
    sorted_values = values[sort_idx]
    sorted_weights = weights[sort_idx]

    group_values, group_starts = np.unique(sorted_values, return_index=True)
    group_weights = np.add.reduceat(sorted_weights, group_starts)
    group_weighted_values = group_values * group_weights
    cumulative_group_weights = cumsum(group_weights)

    target_weight = rank_from_bottom * cumulative_group_weights[-1]
    boundary_group = int(np.searchsorted(cumulative_group_weights, target_weight, side="left"))

    weight_below = cumulative_group_weights[boundary_group - 1] if boundary_group > 0 else 0.0
    share_below = group_weighted_values[:boundary_group].sum() if boundary_group > 0 else 0.0
    boundary_fraction = (target_weight - weight_below) / group_weights[boundary_group]

    return float((share_below + boundary_fraction * group_weighted_values[boundary_group]) / total)


def gini(
    values: np.ndarray | pd.Series,
    weights: Optional[np.ndarray | pd.Series] = None,
) -> float:
    """Computes Gini coefficient (normalized to 1).
    # Using fastgini formula :
    #             i=N      j=i
    #             SUM W_i*(SUM W_j*X_j - W_i*X_i/2)
    #             i=1      j=1
    # G = 1 - 2* ----------------------------------
    #                 i=N             i=N
    #                 SUM W_i*X_i  *  SUM W_i
    #                 i=1             i=1
    # where observations are sorted in ascending order of X.
    # From http://fmwww.bc.edu/RePec/bocode/f/fastgini.html

    Args:
      values: Vector of values
      weights: Weights vector (Default value = None)

    Returns:
        float: Gini
    """
    values = asarray(values, dtype=float)
    if weights is None:
        weights = ones(len(values))
    weights = asarray(weights, dtype=float)

    sort_idx = argsort(values)
    x = values[sort_idx]
    w = weights[sort_idx]
    wx = w * x

    cdf = cumsum(wx) - 0.5 * wx
    numerator = (w * cdf).sum()
    denominator = wx.sum() * w.sum()
    gini = 1 - 2 * (numerator / denominator)

    return gini


def kakwani(
    values: np.ndarray | pd.Series,
    ineq_axis: np.ndarray | pd.Series,
    weights: Optional[np.ndarray | pd.Series] = None,
) -> float:
    """Computes the Kakwani index

    Args:
      values: Vector of values
      ineq_axis: Inequality axis
      weights: Weights vector (Default value = None)

    Returns:
        float: Kakwani index
    """
    from scipy.integrate import simps

    if weights is None:
        weights = ones(len(values))

    plcx, plcy = pseudo_lorenz(values, ineq_axis, weights)
    lcx, lcy = lorenz(ineq_axis, weights)

    del plcx

    return simps((lcy - plcy), lcx)


def lorenz(
    values: np.ndarray | pd.Series,
    weights: Optional[np.ndarray | pd.Series] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Computes Lorenz curve coordinates (x, y)

    Args:
      values: Vector of values
      weights: Weights vector (Default value = None)

    Returns:
        (np.array, np.array): Lorenz curve coordinates
    """
    values = asarray(values, dtype=float)
    if weights is None:
        weights = ones(len(values))
    weights = asarray(weights, dtype=float)

    sort_idx = argsort(values)
    v = values[sort_idx]
    w = weights[sort_idx]

    x = cumsum(w)
    x = x / x[-1]
    y = cumsum(v * w)
    y = y / y[-1]

    return x, y


def mark_weighted_percentiles(
    a: np.ndarray | pd.Series,
    labels: np.ndarray | list,
    weights: np.ndarray | pd.Series,
    method: int,
    return_quantiles: bool = False,
) -> np.ndarray | tuple[np.ndarray, list[float]]:
    """

    Args:
      a:
      labels:
      weights:
      method:
      return_quantiles:  (Default value = False)

    Returns:

    """
    # from http://pastebin.com/KTLip9ee
    # a is an input array of values.
    # weights is an input array of weights, so weights[i] goes with a[i]
    # labels are the names you want to give to the xtiles
    # method refers to which weighted algorithm.
    #      1 for wikipedia, 2 for the stackexchange post.

    # The code outputs an array the same shape as 'a', but with
    # labels[i] inserted into spot j if a[j] falls in x-tile i.
    # The number of xtiles requested is inferred from the length of 'labels'.

    np.random.seed(42)

    # First method, "vanilla" weights from Wikipedia article.
    if method == 1:
        # Sort the values and apply the same sort to the weights.
        n = len(a)
        sort_indx = argsort(a)
        tmp_a = a[sort_indx].copy()
        tmp_weights = weights[sort_indx].copy()

        # 'labels' stores the name of the x-tiles the user wants,
        # and it is assumed to be linearly spaced between 0 and 1
        # so 5 labels implies quintiles, for example.
        num_categories = len(labels)
        breaks = linspace(0, 1, num_categories + 1)

        # Compute the percentile values at each explicit data point in a.
        cu_weights = cumsum(tmp_weights)
        p_vals = (1.0 / cu_weights[-1]) * (cu_weights - 0.5 * tmp_weights)

        # Set up the output array.
        ret = repeat(0, len(a))
        if len(a) < num_categories:
            return ret

        # Set up the array for the values at the breakpoints.
        quantiles = []

        # Find the two indices that bracket the breakpoint percentiles.
        # then do interpolation on the two a_vals for those indices, using
        # interp-weights that involve the cumulative sum of weights.
        for brk in breaks:
            if brk <= p_vals[0]:
                i_low = 0
                i_high = 0
            elif brk >= p_vals[-1]:
                i_low = n - 1
                i_high = n - 1
            else:
                for ii in range(n - 1):
                    if (p_vals[ii] <= brk) and (brk < p_vals[ii + 1]):
                        i_low = ii
                        i_high = ii + 1

            if i_low == i_high:
                v = tmp_a[i_low]
            else:
                # If there are two brackets, then apply the formula as per Wikipedia.
                v = tmp_a[i_low] + ((brk - p_vals[i_low]) / (p_vals[i_high] - p_vals[i_low])) * (
                    tmp_a[i_high] - tmp_a[i_low]
                )

            # Append the result.
            quantiles.append(v)

        # Now that the weighted breakpoints are set, just categorize
        # the elements of a with logical indexing.
        for i in range(0, len(quantiles) - 1):
            lower = quantiles[i]
            upper = quantiles[i + 1]
            ret[and_(a >= lower, a < upper)] = labels[i]

        # make sure upper and lower indices are marked
        ret[a <= quantiles[0]] = labels[0]
        ret[a >= quantiles[-1]] = labels[-1]

        return ret

    # The stats.stackexchange suggestion.
    elif method == 2:
        n = len(a)
        sort_indx = argsort(a)
        tmp_a = a[sort_indx].copy()
        tmp_weights = weights[sort_indx].copy()

        num_categories = len(labels)
        breaks = linspace(0, 1, num_categories + 1)

        cu_weights = cumsum(tmp_weights)

        # Formula from stats.stackexchange.com post.
        s_vals = [0.0]
        for ii in range(1, n):
            s_vals.append(ii * tmp_weights[ii] + (n - 1) * cu_weights[ii - 1])
        s_vals = asarray(s_vals)

        # Normalized s_vals for comapring with the breakpoint.
        norm_s_vals = (1.0 / s_vals[-1]) * s_vals

        # Set up the output variable.
        ret = repeat(0, n)
        if num_categories > n:
            return ret

        # Set up space for the values at the breakpoints.
        quantiles = []

        # Find the two indices that bracket the breakpoint percentiles.
        # then do interpolation on the two a_vals for those indices, using
        # interp-weights that involve the cumulative sum of weights.
        for brk in breaks:
            if brk <= norm_s_vals[0]:
                i_low = 0
                i_high = 0
            elif brk >= norm_s_vals[-1]:
                i_low = n - 1
                i_high = n - 1
            else:
                for ii in range(n - 1):
                    if (norm_s_vals[ii] <= brk) and (brk < norm_s_vals[ii + 1]):
                        i_low = ii
                        i_high = ii + 1

            if i_low == i_high:
                v = tmp_a[i_low]
            else:
                # Interpolate as in the method 1 method, but using the s_vals instead.
                v = tmp_a[i_low] + (((brk * s_vals[-1]) - s_vals[i_low]) / (s_vals[i_high] - s_vals[i_low])) * (
                    tmp_a[i_high] - tmp_a[i_low]
                )
            quantiles.append(v)

        # Now that the weighted breakpoints are set, just categorize
        # the elements of a as usual.
        for i in range(0, len(quantiles) - 1):
            lower = quantiles[i]
            upper = quantiles[i + 1]
            ret[and_(a >= lower, a < upper)] = labels[i]

        # make sure upper and lower indices are marked
        ret[a <= quantiles[0]] = labels[0]
        ret[a >= quantiles[-1]] = labels[-1]

        if return_quantiles:
            return ret, quantiles
        else:
            return ret


def pseudo_lorenz(
    values: np.ndarray | pd.Series,
    ineq_axis: np.ndarray | pd.Series,
    weights: Optional[np.ndarray | pd.Series] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Computes The pseudo Lorenz Curve coordinates

    Args:
      values:
      ineq_axis:
      weights:  (Default value = None)

    Returns:

    """
    values = asarray(values, dtype=float)
    ineq_axis = asarray(ineq_axis, dtype=float)
    if weights is None:
        weights = ones(len(values))
    weights = asarray(weights, dtype=float)

    sort_idx = argsort(ineq_axis)
    v = values[sort_idx]
    w = weights[sort_idx]

    x = cumsum(w)
    x = x / x[-1]
    y = cumsum(v * w)
    y = y / y[-1]

    return x, y


def bottom_share(
    values: np.ndarray | pd.Series,
    rank_from_bottom: float,
    weights: Optional[np.ndarray | pd.Series] = None,
) -> float:
    """

    Args:
      values(np.array): Vector of values
      rank_from_bottom(float): Rank from bottom (bottom is 0 and top is 1)
      weights(np.array): Weights vector (Default value = None)

    Returns:

    """
    return _weighted_bottom_share(values, rank_from_bottom, weights)


def top_share(
    values: np.ndarray | pd.Series,
    rank_from_top: float,
    weights: Optional[np.ndarray | pd.Series] = None,
) -> float:
    """

    Args:
      values(np.array): Vector of values
      rank_from_top(float): Rank from top (bottom is 1 and top is 0)
      weights(np.array): Weights vector (Default value = None)

    Returns:

    """
    if not 0 <= rank_from_top <= 1:
        raise ValueError("rank_from_top must be between 0 and 1")
    return 1 - _weighted_bottom_share(values, 1 - rank_from_top, weights)


def weighted_quantiles(
    data: np.ndarray | pd.Series,
    labels: np.ndarray | list,
    weights: np.ndarray | pd.Series,
    return_quantiles: bool = False,
) -> np.ndarray | tuple[np.ndarray, list[float]]:
    num_categories = len(labels)
    breaks = linspace(0, 1, num_categories + 1)
    data = asarray(data, dtype=float)
    weights = asarray(weights, dtype=float)
    quantiles = [_weighted_quantile(data, weights, mybreak) for mybreak in breaks[1:]]

    ret = zeros(len(data))
    for i in range(0, len(quantiles) - 1):
        lower = quantiles[i]
        upper = quantiles[i + 1]
        ret[and_(data > lower, data <= upper)] = labels[i]

    if return_quantiles:
        return ret + 1, quantiles
    else:
        return ret + 1


def weightedcalcs_quantiles(
    data: np.ndarray | pd.Series,
    labels: np.ndarray | list,
    weights: np.ndarray | pd.Series,
    return_quantiles: bool = False,
) -> np.ndarray | tuple[np.ndarray, list[float]]:
    calc = wc.Calculator("weights")
    num_categories = len(labels)
    breaks = linspace(0, 1, num_categories + 1)
    data_frame = pd.DataFrame(
        {
            "weights": weights,
            "data": data,
        }
    )
    quantiles = [calc.quantile(data_frame, "data", mybreak) for mybreak in breaks[1:]]

    ret = zeros(len(data))
    for i in range(0, len(quantiles) - 1):
        lower = quantiles[i]
        upper = quantiles[i + 1]
        ret[and_(data > lower, data <= upper)] = labels[i]

    if return_quantiles:
        return ret + 1, quantiles
    else:
        return ret + 1
