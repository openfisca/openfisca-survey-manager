# -*- coding: utf-8 -*-


from __future__ import division

import logging
import operator

from numpy import exp, ones, zeros, unique, array, dot, float64


log = logging.getLogger(__name__)


def linear(u):
    return 1 + u


def linear_prime(u):
    return ones(u.shape, dtype = float)


def raking_ratio(u):
    return exp(u)


def raking_ratio_prime(u):
    return exp(u)


def logit(u, low, up):
    a = (up - low) / ((1 - low) * (up - 1))
    return (low * (up - 1) + up * (1 - low) * exp(a * u)) / (up - 1 + (1 - low) * exp(a * u))


def logit_prime(u, low, up):
    a = (up - low) / ((1 - low) * (up - 1))
    return (
        (a * up * (1 - low) * exp(a * u)) * (up - 1 + (1 - low) * exp(a * u))
        - (low * (up - 1) + up * (1 - low) * exp(a * u)) * (1 - low) * a * exp(a * u)
        ) / (up - 1 + (1 - low) * exp(a * u)) ** 2


def build_dummies_dict(data):
    """
        Return a dict with unique values as keys and vectors as values
    """
    unique_val_list = unique(data)
    output = {}
    for val in unique_val_list:
        output[val] = (data == val)
    return output


def calmar(data_in, margins, pondini = 'wprm_init', method = 'linear', lo = None, up = None, use_proportions = False,
        xtol = 1.49012e-08, maxfev = 256):
    """
        Calibrate weights to satisfy some margin constraints

        :param dataframe data_in: The observations data
        :param str pondini: The initial weight variable name
        :param dict margins: Margins is a dictionnary containing for each variable as key the following values
            - a scalar for numeric variables
            - a dictionnary with categories as key and populations as values
            - eventually a key named `total_population` with value the total population. If absent it is initialized to the actual total population

        :param str method: Should be 'linear', 'raking ratio' or 'logit'
        :param float lo: lower bound on weights ratio. Mandatory when using logit method. Should be < 1.
        :param float up: upper bound on weights ratio. Mandatory when using logit method. Should be > 1.
        :param bool use_proportions: default to False. if True use proportions if total population from margins doesn't match total population
        :param xtol: relative precision on lagrangian multipliers. By default xtol = 1.49012e-08 (default fsolve xtol)
        :param maxfev: maximum number of function evaluation default to 256
    """

    from scipy.optimize import fsolve

    # remove null weights and keep original data
    null_weight_observations = data_in[pondini].isnull().sum()
    if null_weight_observations > 0:
        log.info("{} observations have a NaN weight. Not used in the calibration.".format(null_weight_observations))

    is_non_zero_weight = (data_in[pondini].fillna(0) > 0)
    if is_non_zero_weight.sum() > null_weight_observations:
        log.info("{} observations have a zero weight. Not used in the calibration.".format(
            (data_in[pondini].fillna(0) <= 0).sum() - null_weight_observations))

    variables = set(margins.keys()).intersection(set(data_in.columns))
    for variable in variables:
        null_value_observations = data_in[variable].isnull().sum()
        if null_value_observations > 0:
            log.info("For variable {}, {} observations have a NaN value. Not used in the calibration.".format(
                variable, null_value_observations))
            is_non_zero_weight = is_non_zero_weight & data_in[variable].notnull()

    if not is_non_zero_weight.all():
        log.info("We drop {} observations.".format((~is_non_zero_weight).sum()))

    data = dict()
    for a in data_in.columns:
        data[a] = data_in.loc[is_non_zero_weight, a].copy()

    if not margins:
        raise Exception("Calmar requires non empty dict of margins")

    # choose method
    if method == 'linear':
        F = linear
        F_prime = linear_prime
    elif method == 'raking ratio':
        F = raking_ratio
        F_prime = raking_ratio_prime
    elif method == 'logit':
        assert up is not None, "When method == 'logit', a value > 1 for up is mandatory"
        assert up > 1, "up should be > 1"
        assert lo is not None, "When method == 'logit', a value < 1 for lo is mandatory"
        assert lo < 1, "lo should be < 1"
        def F(x):
            return logit(x, parameters['lo'], parameters['up'])

        def F_prime(x):
            return logit_prime(x, parameters['lo'], parameters['up'])
    else:
        raise ValueError("method should be 'linear', 'raking ratio' or 'logit'")

    # Construction observations matrix
    if 'total_population' in margins:
        total_population = margins.pop('total_population')
    else:
        total_population = data[pondini].fillna(0).sum()

    nk = len(data[pondini])
    # number of Lagrange parameters (at least total population)
    nj = 1

    margins_new = {}
    margins_new_dict = {}
    for var, val in margins.items():
        if isinstance(val, dict):
            dummies_dict = build_dummies_dict(data[var])
            k, pop = 0, 0
            for cat, nb in val.items():
                cat_varname = var + '_' + str(cat)
                data[cat_varname] = dummies_dict[cat]
                margins_new[cat_varname] = nb
                if var not in margins_new_dict:
                    margins_new_dict[var] = {}
                margins_new_dict[var][cat] = nb
                pop += nb
                k += 1
                nj += 1
            # Check total popualtion
            if pop != total_population:
                if use_proportions:
                    log.info(
                        'calmar: categorical variable {} is inconsistent with population; using proportions'.format(
                            var
                            )
                        )
                    for cat, nb in val.items():
                        cat_varname = var + '_' + str(cat)
                        margins_new[cat_varname] = nb * total_population / pop
                        margins_new_dict[var][cat] = nb * total_population / pop
                else:
                    raise Exception('calmar: categorical variable {} weights sums up to {} != {}'.format(
                        var, pop, total_population))
        else:
            margins_new[var] = val
            margins_new_dict[var] = val
            nj += 1

    # On conserve systematiquement la population
    if hasattr(data, 'dummy_is_in_pop'):
        raise Exception('dummy_is_in_pop is not a valid variable name')

    data['dummy_is_in_pop'] = ones(nk)
    margins_new['dummy_is_in_pop'] = total_population

    # paramètres de Lagrange initialisés à zéro
    lambda0 = zeros(nj)

    # initial weights
    d = data[pondini].values
    x = zeros((nk, nj))  # nb obs x nb constraints
    xmargins = zeros(nj)
    margins_dict = {}
    j = 0
    for var, val in margins_new.items():
        x[:, j] = data[var]
        xmargins[j] = val
        margins_dict[var] = val
        j += 1

    # Résolution des équations du premier ordre
    def constraint(l):
        return dot(d * F(dot(x, l)), x) - xmargins

    def constraint_prime(l):
        return dot(d * (x.T * F_prime(dot(x, l))), x)
        # le jacobien ci-dessus est constraintprime = @(l) x*(d.*Fprime(x'*l)*x');

    tries, ier = 0, 2
    err_max = 1
    conv = 1
    while (ier == 2 or ier == 5 or ier == 4) and not (tries >= 10 or (err_max < 1e-6 and conv < 1e-8)):
        lambdasol, infodict, ier, mesg = fsolve(
            constraint,
            lambda0,
            fprime = constraint_prime,
            maxfev = maxfev,
            xtol = xtol,
            full_output = 1,
            )
        lambda0 = 1 * lambdasol
        tries += 1

        pondfin = d * F(dot(x, lambdasol))
        rel_error = {}
        for var, val in margins_new.items():
            rel_error[var] = abs((data[var] * pondfin).sum() - margins_dict[var]) / margins_dict[var]
        sorted_err = sorted(rel_error.items(), key = operator.itemgetter(1), reverse = True)

        conv = abs(err_max - sorted_err[0][1])
        err_max = sorted_err[0][1]

    if (ier == 2 or ier == 5 or ier == 4):
        log.debug("optimization converged after {} tries".format(tries))

    # rebuilding a weight vector with the same size of the initial one
    pondfin_out = array(data_in[pondini], dtype = float64)
    pondfin_out[is_non_zero_weight] = pondfin
    return pondfin_out, lambdasol, margins_new_dict


def check_calmar(data_in, margins, pondini='wprm_init', pondfin_out = None, lambdasol = None, margins_new_dict = None):
    for variable, margin in margins.items():
        if variable != 'total_population':
            print(variable, margin, abs(margin - margins_new_dict[variable]) / abs(margin))
