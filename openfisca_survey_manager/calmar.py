"""CALMAR: Calibrates weights to satisfy margins constraints."""

import logging
import operator

import pandas as pd
from numpy import array, dot, exp, float64, log as ln, ones, sqrt, unique, zeros

log = logging.getLogger(__name__)


class CalmarError(Exception):
    """Custom exception for CALMAR calibration errors."""


def linear(u):
    """Args:
      u: Argument of the function.

    Returns: 1 + u

    """
    return 1 + u


def linear_prime(u):
    """Args:
      u: Argument of the function.

    Returns: 1

    """
    return ones(u.shape, dtype=float)


def raking_ratio(u):
    """Args:
      u: Argument of the function.

    Returns: exp(u)

    """
    return exp(u)


def raking_ratio_prime(u):
    """Args:
      u: Argument of the function.

    Returns: exp(u)

    """
    return exp(u)


def logit(u, low, up):
    """Args:
      u: Argument of the function.
      low: Lower bound.
      up: Upper bound.

    Returns: Logit transformation.

    """
    a = (up - low) / ((1 - low) * (up - 1))
    return (low * (up - 1) + up * (1 - low) * exp(a * u)) / (
        up - 1 + (1 - low) * exp(a * u)
    )


def logit_prime(u, low, up):
    """Args:
      u: Argument of the function.
      low: Lower bound.
      up: Upper bound.

    Returns: Derivative of Logit transformation.
    """
    a = (up - low) / ((1 - low) * (up - 1))
    return (
        (a * up * (1 - low) * exp(a * u)) * (up - 1 + (1 - low) * exp(a * u))
        - (low * (up - 1) + up * (1 - low) * exp(a * u)) * (1 - low) * a * exp(a * u)
    ) / (up - 1 + (1 - low) * exp(a * u)) ** 2


def hyperbolic_sinus(u, alpha):
    logarithm = ln(2 * alpha * u + sqrt(4 * (alpha**2) * (u**2) + 1))
    return 0.5 * (logarithm / alpha + sqrt((logarithm / alpha) ** 2 + 4))


def hyperbolic_sinus_prime(u, alpha):
    square = sqrt(4 * (alpha**2) * (u**2) + 1)
    return 0.5 * (
        ((4 * (alpha**2) * u) / square + 2 * alpha) / (alpha * (square + 2 * alpha * u))
        + ((4 * (alpha**2) * u / square + 2 * alpha) * ln(square + 2 * alpha * u))
        / (
            (alpha**2)
            * (square + 2 * alpha * u)
            * sqrt((ln(square + 2 * alpha * u) ** 2) + 4)
        )
    )


def build_dummies_dict(data):
    """Build a dictionary of dummy variables from the input data.

    Args:
      data: A pandas Series or DataFrame.

    Returns:
      A dictionary where the keys are the unique values in the data and the values are boolean masks.
    """
    unique_val_list = unique(data)
    output = {}
    for val in unique_val_list:
        output[val] = data == val
    return output


def calmar(
    data_in,
    margins: dict,
    initial_weight: str,
    method="linear",
    lo=None,
    up=None,
    alpha=None,
    use_proportions: bool = False,
    xtol: float = 1.49012e-08,
    maxfev: int = 256,
):
    """Calibrates weights to satisfy margins constraints.

    Args:
        data_in (pd.DataFrame): The observations data by entity + a dictionary to identify the target entity
        margins (dict): Margins is a dictionnary containing for each variable as key the following values
          - a scalar for numeric variables
          - a dictionnary with categories as key and populations as values
          - eventually a key named `total_population` with value the total population. If absent it is initialized to the actual total population
          - eventually a key named `total_population_smaller_entity` with value the total number of the second entity. If absent it is initialized to the actual total population

        initial_weight (str): Initial weight variable.
        method (str, optional): Calibration method. Should be 'linear', 'raking ratio', 'logit' or 'hyperbolic sinus'. Defaults to 'linear'.
        lo (float, optional): Lower bound on weights ratio. Mandatory when using logit method. Should be < 1. Defaults to None.
        up (float, optional): Upper bound on weights ratio. Mandatory when using logit method. Should be > 1. Defaults to None.
        alpha (float, optional): Bound on weights ratio. Mandatory when using hyperbolic sinus method. Should be > 0. Defaults to None.
        use_proportions (bool, optional): When True use proportions if total population from margins doesn't match total population. Defaults to False.
        xtol (float, optional): Relative precision on lagrangian multipliers.  Defaults to 1.49012e-08 (fsolve xtol).
        maxfev (int, optional): Maximum number of function evaluation. Defaults to 256.

    Raises:
        Exception: [description]
        Exception: [description]
        Exception: [description]

    Returns:
        np.array: Margins adjusting weights
        float: Lagrangian parameter
        dict: Updated margins

    Sources:
        https://github.com/InseeFrLab/Calmar2/blob/main/manuel_utilisation.pdf
    """
    from scipy.optimize import fsolve  # noqa

    target_entity = data_in["target_entity_name"]
    smaller_entity = None
    entities = [target_entity]
    for key in data_in:
        if key not in ("target_entity_name", target_entity):
            smaller_entity = key
            entities += [smaller_entity]

    # remove null weights and keep original data
    null_weight_observations = data_in[target_entity][initial_weight].isna().sum()
    if null_weight_observations > 0:
        log.info(
            f"{null_weight_observations} observations have a NaN weight. Not used in the calibration."
        )

    is_non_zero_weight = data_in[target_entity][initial_weight].fillna(0) > 0
    if is_non_zero_weight.sum() > null_weight_observations:
        log.info(
            "%s observations have a zero weight. Not used in the calibration.",
            (data_in[target_entity][initial_weight].fillna(0) <= 0).sum()
            - null_weight_observations,
        )

    variables = set(margins.keys()).intersection(set(data_in[target_entity].columns))
    for variable in variables:
        null_value_observations = data_in[target_entity][variable].isna().sum()
        if null_value_observations > 0:
            log.info(
                f"For variable {variable}, {null_value_observations} observations have a NaN value. Not used in the calibration."
            )
            is_non_zero_weight = (
                is_non_zero_weight & data_in[target_entity][variable].notna()
            )

    if not is_non_zero_weight.all():
        log.info(f"We drop {(~is_non_zero_weight).sum()} observations.")

    data = {}
    if smaller_entity:
        data[smaller_entity] = pd.DataFrame()
        for col in data_in[smaller_entity].columns:
            data[smaller_entity][col] = data_in[smaller_entity][col].copy()
    data[target_entity] = pd.DataFrame()
    for col in data_in[target_entity].columns:
        data[target_entity][col] = (
            data_in[target_entity].loc[is_non_zero_weight, col].copy()
        )

    if not margins:
        msg = "Calmar requires non empty dict of margins"
        raise CalmarError(msg)

    # choose method
    assert method in ["linear", "raking ratio", "logit", "hyperbolic sinus"], (
        "method should be 'linear', 'raking ratio', 'logit' or 'hyperbolic sinus'"
    )
    if method == "linear":
        f = linear
        f_prime = linear_prime
    elif method == "raking ratio":
        f = raking_ratio
        f_prime = raking_ratio_prime
    elif method == "logit":
        assert up is not None, "When method == 'logit', a value > 1 for up is mandatory"
        assert up > 1, "up should be > 1"
        assert lo is not None, "When method == 'logit', a value < 1 for lo is mandatory"
        assert lo < 1, "lo should be < 1"

        def f(x):
            return logit(x, lo, up)

        def f_prime(x):
            return logit_prime(x, lo, up)
    elif method == "hyperbolic sinus":
        assert alpha is not None, (
            "When method == 'hyperbolic sinus', a value > 0 for alpha is mandatory"
        )
        assert alpha > 0, "alpha should be > 0"

        def f(x):
            return hyperbolic_sinus(x, alpha)

        def f_prime(x):
            return hyperbolic_sinus_prime(x, alpha)

    margins = margins.copy()
    # Construction observations matrix
    if "total_population" in margins:
        total_population = margins.pop("total_population")
    else:
        total_population = data[target_entity][initial_weight].fillna(0).sum()
    if smaller_entity is not None:
        if "total_population_smaller_entity" in margins:
            total_population_smaller_entity = margins.pop(
                "total_population_smaller_entity"
            )
        else:
            total_population_smaller_entity = (
                total_population * len(data[smaller_entity]) / len(data[target_entity])
            )
    else:
        total_population_smaller_entity = 0

    nk = len(data[target_entity][initial_weight])
    # number of Lagrange parameters (at least total population, and potentially total population 2)
    nj = 1 + (smaller_entity is not None)

    margins_new = {}
    margins_new_dict = {}
    for entity in list(entities):
        for var, val in margins.items():
            if var in data[entity].columns:
                if isinstance(val, dict):
                    dummies_dict = build_dummies_dict(data[entity][var])
                    _k, pop = 0, 0
                    list_col_to_add = [data[entity]]
                    for cat, nb in val.items():
                        cat_varname = var + "_" + str(cat)
                        list_col_to_add.append(
                            pd.Series(dummies_dict[cat], name=cat_varname)
                        )
                        margins_new[cat_varname] = nb
                        if var not in margins_new_dict:
                            margins_new_dict[var] = {}
                        margins_new_dict[var][cat] = nb
                        pop += nb
                        nj += 1
                    data[entity] = pd.concat(list_col_to_add, axis=1)
                    # Check total popualtion
                    population = (entity == target_entity) * total_population + (
                        entity != target_entity
                    ) * total_population_smaller_entity
                    if pop != population:
                        if use_proportions:
                            log.info(
                                f"calmar: categorical variable {var} is inconsistent with population; using proportions"
                            )
                            for cat, nb in val.items():
                                cat_varname = var + "_" + str(cat)
                                margins_new[cat_varname] = nb * population / pop
                                margins_new_dict[var][cat] = nb * population / pop
                        else:
                            msg = f"calmar: categorical variable {var} weights sums up to {pop} != {population}"
                            raise CalmarError(msg)
                else:
                    margins_new[var] = val
                    margins_new_dict[var] = val
                    nj += 1

    # On conserve systematiquement la population
    if hasattr(data, "dummy_is_in_pop") or hasattr(
        data, "dummy_is_in_pop_smaller_entity"
    ):
        msg = "dummy_is_in_pop and dummy_is_in_pop_smaller_entity are not valid variable names"
        raise CalmarError(msg)

    data[target_entity]["dummy_is_in_pop"] = ones(nk)
    margins_new["dummy_is_in_pop"] = total_population
    if smaller_entity:
        data[smaller_entity]["dummy_is_in_pop_smaller_entity"] = ones(
            len(data[smaller_entity]["id_variable"])
        )
        margins_new["dummy_is_in_pop_smaller_entity"] = total_population_smaller_entity
    data_final = data[target_entity]

    if smaller_entity:
        liste_col_to_sum = [
            variable for variable in data[smaller_entity] if variable != "id_variable"
        ]
        dic_agg = {}
        for variable_to_sum in liste_col_to_sum:
            dic_agg[variable_to_sum] = "sum"
        data_second = data[smaller_entity].groupby("id_variable").agg(dic_agg)
        data_final = data_second.merge(data[target_entity], on="id_variable")
        nk = len(data_final[initial_weight])

    # paramètres de Lagrange initialisés à zéro
    lambda0 = zeros(nj)

    # initial weights
    d = data_final[initial_weight].to_numpy()
    x = zeros((nk, nj))  # nb obs x nb constraints
    xmargins = zeros(nj)
    margins_dict = {}
    for j, (var, val) in enumerate(margins_new.items()):
        x[:, j] = data_final[var]
        xmargins[j] = val
        margins_dict[var] = val

    # Résolution des équations du premier ordre
    def constraint(lambda_):
        return dot(d * f(dot(x, lambda_)), x) - xmargins

    def constraint_prime(lambda_):
        return dot(d * (x.T * f_prime(dot(x, lambda_))), x)
        # le jacobien ci-dessus est constraintprime = @(lambda) x*(d.*Fprime(x'*lambda)*x');

    tries, ier = 0, 2
    err_max = 1
    conv = 1
    while (ier in {2, 5, 4}) and not (tries >= 10 or (err_max < 1e-6 and conv < 1e-8)):
        lambdasol, infodict, ier, mesg = fsolve(
            constraint,
            lambda0,
            fprime=constraint_prime,
            maxfev=maxfev,
            xtol=xtol,
            full_output=1,
        )
        lambda0 = 1 * lambdasol
        tries += 1

        pondfin = d * f(dot(x, lambdasol))
        rel_error = {}
        for var, val in margins_new.items():  # noqa analysis:ignore
            rel_error[var] = (
                abs((data_final[var] * pondfin).sum() - margins_dict[var])
                / margins_dict[var]
            )
        sorted_err = sorted(rel_error.items(), key=operator.itemgetter(1), reverse=True)

        conv = abs(err_max - sorted_err[0][1])
        err_max = sorted_err[0][1]

    if ier in {2, 5, 4}:
        log.debug(f"optimization converged after {tries} tries")

    # rebuilding a weight vector with the same size of the initial one
    pondfin_out = array(data_in[target_entity][initial_weight], dtype=float64)
    pondfin_out[is_non_zero_weight] = pondfin

    del infodict, mesg  # TODO: better exploit this information

    return pondfin_out, lambdasol, margins_new_dict
