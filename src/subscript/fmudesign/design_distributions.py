# -*- coding: utf-8 -*-
"""Module for random sampling of parameter values from
distributions. For use in generation of design matrices
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from math import exp
import re
import numpy
import numpy.linalg as la
import scipy.stats
import pandas as pd


def _check_dist_params_normal(dist_params):
    if len(dist_params) != 2 and len(dist_params) != 4:
        status = False
        msg = (
            "Normal distribution must have 2 parameters"
            " or 4 for a truncated normal, "
            "but had " + str(len(dist_params)) + " parameters. "
        )
    elif not all(is_number(param) for param in dist_params):
        status = False
        msg = "Parameters for normal distribution must be numbers. "
    elif float(dist_params[1]) < 0:
        status = False
        msg = "Stddev for normal distribution must be >= 0. "
    else:
        status = True
        msg = ""

    return status, msg


def _check_dist_params_lognormal(dist_params):
    if len(dist_params) != 2:
        status = False
        msg = (
            "Lognormal distribution must have 2 parameters, "
            "but had " + str(len(dist_params)) + " parameters. "
        )
    elif not (is_number(dist_params[0]) and is_number(dist_params[1])):
        status = False
        msg = "Parameters for lognormal distribution must be numbers. "
    elif float(dist_params[1]) < 0:
        status = False
        msg = "Lognormal distribution must have" " stddev >= 0. "
    else:
        status = True
        msg = ""

    return status, msg


def _check_dist_params_uniform(dist_params):
    if len(dist_params) != 2:
        status = False
        msg = (
            "Uniform distribution must have 2 parameters, "
            "but had " + str(len(dist_params)) + " parameters. "
        )
    elif not (is_number(dist_params[0]) and is_number(dist_params[1])):
        status = False
        msg = "Parameters for uniform distribution must be numbers. "
    elif float(dist_params[1]) < float(dist_params[0]):
        status = False
        msg = "Uniform distribution must have dist_param2" " >= dist_param1"
    else:
        status = True
        msg = ""

    return status, msg


def _check_dist_params_triang(dist_params):
    if len(dist_params) != 3:
        status = False
        msg = (
            "Triangular distribution must have 3 parameters, "
            "but had " + str(len(dist_params)) + " parameters. "
        )
    elif not all(is_number(param) for param in dist_params):
        status = False
        msg = "Parameters for triangular distribution must be numbers. "
    elif not (
        (float(dist_params[2]) >= float(dist_params[1]))
        and (float(dist_params[1]) >= float(dist_params[0]))
    ):
        status = False
        msg = "Triangular distribution must have: " "low <= mode <= high. "
    else:
        status = True
        msg = ""

    return status, msg


def _check_dist_params_pert(dist_params):
    if len(dist_params) not in [3, 4]:
        status = False
        msg = (
            "pert distribution must have 3 or 4 parameters, "
            "but had " + str(len(dist_params)) + " parameters. "
        )
    elif not all(is_number(param) for param in dist_params):
        status = False
        msg = "Parameters for pert distribution must be numbers. "
    elif not (
        (float(dist_params[2]) >= float(dist_params[1]))
        and (float(dist_params[1]) >= float(dist_params[0]))
    ):
        status = False
        msg = "Pert distribution must have: " "low <= mode <= high. "
    else:
        status = True
        msg = ""

    return status, msg


def _check_dist_params_logunif(dist_params):
    if len(dist_params) != 2:
        status = False
        msg = (
            "Log uniform distribution must have 2 parameters. "
            "but had " + str(len(dist_params)) + " parameters. "
        )
    elif not (is_number(dist_params[0]) and is_number(dist_params[1])):
        status = False
        msg = "Parameters for log uniform distribution must be numbers. "
    elif not (
        (float(dist_params[0]) > 0) and (float(dist_params[1]) >= float(dist_params[0]))
    ):
        status = False
        msg = "loguniform distribution must have" " low > 0 and high >=low. "
    else:
        status = True
        msg = ""

    return status, msg


def draw_values_normal(dist_parameters, numreals, normalscoresamples=None):
    """Draws values from normal distribution.

    Args:
        dist_parameters(list): [mean, std dev, min, max],
            min/max defining truncated normal
        numreals(int): number of realisations to draw
        normalscoresamples(list): samples for correlated parameters

    Returns:
        list of values
    """

    distribution = None
    if len(dist_parameters) == 2:  # normal
        status, msg = _check_dist_params_normal(dist_parameters)
        if status:
            dist_mean = float(dist_parameters[0])
            dist_stddev = float(dist_parameters[1])
            if normalscoresamples is not None:
                values = scipy.stats.norm.ppf(
                    scipy.stats.norm.cdf(normalscoresamples),
                    loc=dist_mean,
                    scale=dist_stddev,
                )
            else:
                distribution = scipy.stats.norm(dist_mean, dist_stddev)
                values = distribution.rvs(size=numreals)
        else:
            raise ValueError(msg)

    else:  # truncated normal or invalid
        status, msg = _check_dist_params_normal(dist_parameters)
        if status:
            mean = float(dist_parameters[0])
            sigma = float(dist_parameters[1])
            clip1 = float(dist_parameters[2])
            clip2 = float(dist_parameters[3])
            low = (clip1 - mean) / sigma
            high = (clip2 - mean) / sigma
            if normalscoresamples is not None:
                values = scipy.stats.truncnorm.ppf(
                    scipy.stats.norm.cdf(normalscoresamples),
                    low,
                    high,
                    loc=mean,
                    scale=sigma,
                )
            else:
                distribution = scipy.stats.truncnorm(low, high, loc=mean, scale=sigma)
                values = distribution.rvs(size=numreals)
        else:
            raise ValueError(msg)
    return values


def draw_values_lognormal(dist_parameters, numreals, normalscoresamples=None):
    """Draws values from lognormal distribution.

    Args:
        dist_parameters(list): [mu, sigma] for the logarithm of the variable
        numreals(int): number of realisations to draw
        normalscoresamples(list): samples for correlated parameters

    Returns:
        list of values
    """
    distribution = None
    status, msg = _check_dist_params_lognormal(dist_parameters)
    if status:
        mean = float(dist_parameters[0])
        sigma = float(dist_parameters[1])
        if normalscoresamples is not None:
            values = scipy.stats.lognorm.ppf(
                scipy.stats.norm.cdf(normalscoresamples),
                s=sigma,
                loc=0,
                scale=exp(mean),
            )
        else:
            distribution = scipy.stats.lognorm(s=sigma, scale=exp(mean))
            values = distribution.rvs(size=numreals)
    else:
        raise ValueError(msg)
    return values


def draw_values_uniform(dist_parameters, numreals, normalscoresamples=None):
    """Draws values from uniform distribution.

    Args:
        dist_parameters(list): [minimum, maximum]
        numreals(int): number of realisations to draw
        normalscoresamples(list): samples for correlated parameters

    Returns:
        list of values
    """
    distribution = None
    status, msg = _check_dist_params_uniform(dist_parameters)
    if status:
        low = float(dist_parameters[0])
        high = float(dist_parameters[1])
        uscale = high - low
        if normalscoresamples is not None:
            values = scipy.stats.uniform.ppf(
                scipy.stats.norm.cdf(normalscoresamples), loc=low, scale=uscale
            )

        else:
            distribution = scipy.stats.uniform(loc=low, scale=uscale)
            values = distribution.rvs(size=numreals)
    else:
        raise ValueError(msg)
    return values


def draw_values_triangular(dist_parameters, numreals, normalscoresamples=None):
    """Draws values from triangular distribution.

    Args:
        dist_parameters(list): [min, mode,  max]
        numreals(int): number of realisations to draw
        normalscoresamples(list): samples for correlated parameters

    Returns:
        list of values
    """
    status, msg = _check_dist_params_triang(dist_parameters)
    if status:
        low = float(dist_parameters[0])
        mode = float(dist_parameters[1])
        high = float(dist_parameters[2])
        if normalscoresamples is not None:
            if high == low:  # collapsed distribution
                print(
                    "Low and high parameters for triangular distribution"
                    " are equal. Using constant {}".format(low)
                )
                values = scipy.stats.uniform.ppf(
                    scipy.stats.norm.cdf(normalscoresamples), loc=low, scale=0
                )
            else:
                dist_scale = high - low
                shape = (mode - low) / dist_scale
                values = scipy.stats.triang.ppf(
                    scipy.stats.norm.cdf(normalscoresamples),
                    shape,
                    loc=low,
                    scale=dist_scale,
                )
        else:
            if high == low:  # collapsed distribution
                print(
                    "Low and high parameters for triangular distribution"
                    " are equal. Using constant {}".format(low)
                )
                distribution = scipy.stats.uniform(loc=low, scale=0)
                values = distribution.rvs(size=numreals)
            else:
                dist_scale = high - low
                shape = (mode - low) / dist_scale
                distribution = scipy.stats.triang(shape, loc=low, scale=dist_scale)
                values = distribution.rvs(size=numreals)
    else:
        raise ValueError(msg)
    return values


def draw_values_pert(dist_parameters, numreals, normalscoresamples=None):
    """Draws values from pert distribution.

    Args:
        dist_parameters(list): [min, mode,  max, scale]
            where scale is only specified
            for a 4 parameter pert distribution
        numreals(int): number of realisations to draw
        normalscoresamples(list): samples for correlated parameters

    Returns:
        list of values
    """

    status, msg = _check_dist_params_pert(dist_parameters)
    if status:
        low = float(dist_parameters[0])
        mode = float(dist_parameters[1])
        high = float(dist_parameters[2])
        if len(dist_parameters) == 4:
            scale = float(dist_parameters[3])
        else:
            scale = 4  # pert 3 parameter distribution

        if normalscoresamples is not None:
            if high == low:  # collapsed distribution
                print(
                    "Low and high parameters for pert distribution"
                    " are equal. Using constant {}".format(low)
                )
                values = scipy.stats.uniform.ppf(
                    scipy.stats.norm.cdf(normalscoresamples), loc=low, scale=0
                )
            else:
                muval = (low + high + scale * mode) / (scale + 2)
                if muval == mode:
                    alpha1 = (scale / 2) + 1
                else:
                    alpha1 = ((muval - low) * (2 * mode - low - high)) / (
                        (mode - muval) * (high - low)
                    )

                alpha2 = alpha1 * (high - muval) / (muval - low)
                values = scipy.stats.beta.ppf(
                    scipy.stats.norm.cdf(normalscoresamples), alpha1, alpha2
                )
        else:

            if high == low:  # collapsed distribution
                print(
                    "Low and high parameters for pert distribution"
                    " are equal. Using constant {}".format(low)
                )
                distribution = scipy.stats.uniform(loc=low, scale=0)
            else:
                muval = (low + high + scale * mode) / (scale + 2)
                if muval == mode:
                    alpha1 = (scale / 2) + 1
                else:
                    alpha1 = ((muval - low) * (2 * mode - low - high)) / (
                        (mode - muval) * (high - low)
                    )

                alpha2 = alpha1 * (high - muval) / (muval - low)
                distribution = scipy.stats.beta(alpha1, alpha2)
            values = distribution.rvs(size=numreals)

    else:
        raise ValueError(msg)
    # For pert distribution scale afterwards:
    values = values * (dist_parameters[2] - dist_parameters[0]) + dist_parameters[0]

    return values


def draw_values_loguniform(dist_parameters, numreals, normalscoresamples=None):
    """Draws values from loguniform distribution.

    Args:
        dist_parameters(list): [minimum, maximum]
        numreals(int): number of realisations to draw
        normalscoresamples(list): samples for correlated parameters

    Returns:
        list of values
    """

    status, msg = _check_dist_params_logunif(dist_parameters)
    if status:
        low = float(dist_parameters[0])
        high = float(dist_parameters[1])
        if normalscoresamples is not None:
            values = scipy.stats.reciprocal.ppf(
                scipy.stats.norm.cdf(normalscoresamples), low, high
            )
        else:
            distribution = scipy.stats.reciprocal(low, high)
            values = distribution.rvs(size=numreals)
    else:
        raise ValueError(msg)

    return values


def draw_values(distname, dist_parameters, numreals, normalscoresamples=None):
    """
    Prepare scipy distributions with parameters

    Args:
        distname (str): distribution name 'normal', 'lognormal', 'triang',
                        'uniform', 'logunif', 'discrete', 'pert'
        dist_parameters (list): list with parameters for distribution

    Returns:
        scipy.stats distribution with parameters
    """
    if distname[0:4].lower() == "norm":
        values = draw_values_normal(dist_parameters, numreals, normalscoresamples)

    elif distname[0:4].lower() == "logn":
        values = draw_values_lognormal(dist_parameters, numreals, normalscoresamples)

    elif distname[0:4].lower() == "unif":
        values = draw_values_uniform(dist_parameters, numreals, normalscoresamples)

    elif distname[0:6].lower() == "triang":
        values = draw_values_triangular(dist_parameters, numreals, normalscoresamples)

    elif distname[0:4].lower() == "pert":
        values = draw_values_pert(dist_parameters, numreals, normalscoresamples)

    elif distname[0:7].lower() == "logunif":
        values = draw_values_loguniform(dist_parameters, numreals, normalscoresamples)

    elif distname[0:5].lower() == "const":
        if normalscoresamples is not None:
            raise ValueError(
                "Parameter with const distribution "
                "was defined in correlation matrix "
                "but const distribution cannot "
                "be used with correlation. "
            )
        values = [dist_parameters[0]] * numreals

    elif distname[0:4].lower() == "disc":
        if normalscoresamples is not None:
            raise ValueError(
                "Parameter with discrete distribution "
                "was defined in correlation matrix, "
                "but discrete distribution cannot "
                "be used with correlation. "
            )
        status, result = sample_discrete(dist_parameters, numreals)
        if status:
            values = result
        else:
            raise ValueError(result)
    else:
        raise ValueError("distribution name {} is not implemented".format(distname))

    return values


def sample_discrete(dist_params, numreals):
    """Sample from discrete distribution

    Args:
        dist_params(list): parameters for distribution
            dist_params[0] is possible outcomes separated
            by comma
            dist_params[1] is probabilities for each outcome,
            separated by comma
        numreals (int): number of realisations to draw

    Returns:
        numpy.ndarray: values drawn from distribution
    """
    status = True
    outcomes = re.split(",", dist_params[0])
    if len(dist_params) == 2:  # non uniform
        weights = re.split(",", dist_params[1])
        if len(outcomes) != len(weights):
            raise ValueError(
                "Number of weights for discrete distribution "
                "is not the same as number of values."
            )
        else:
            weightnmbr = [float(weight) for weight in weights]
            fractions = [weight / sum(weightnmbr) for weight in weightnmbr]
            values = numpy.random.choice(outcomes, numreals, p=fractions)
    elif len(dist_params) == 1:  # uniform
        values = numpy.random.choice(outcomes, numreals)
    else:
        status = False
        values = "Wrong input for discrete " "distribution"

    return status, values


def is_number(teststring):
    """ Test if a string can be parsed as a float"""
    try:
        if not numpy.isnan(float(teststring)):
            return True
        return False  # It was a "number", but it was NaN.
    except ValueError:
        return False


def read_correlations(corr_dict, corrsheet):
    """Reading correlation info for a
    monte carlo sensitivity

    Args:
        corr_dict (OrderedDict): correlation info

    Returns:
        pandas DataFrame with correlations, parameter names
            as column and index
    """
    correlations = None
    filename = corr_dict["inputfile"]
    if corrsheet in corr_dict["sheetnames"]:
        if filename.endswith(".xlsx"):
            correlations = pd.read_excel(filename, corrsheet, index_col=0)
        else:
            raise ValueError(
                "Correlation matrix filename should be on "
                "Excel format and end with .xlsx "
            )
    else:
        raise ValueError(
            "Corr_sheet {} specified but cannot be "
            "found in list of sheetnames".format(corrsheet)
        )

    return correlations


def make_covariance_matrix(df_correlations, stddevs=None):
    """Read a Pandas DataFrame defining correlation coefficients for
    a set of multivariate normally distributed parameters, and build
    covariance matrix.

    The diagonal of the correlation coefficients matrix should be all
    ones. Variances are combined with the correlation coefficients to
    compute the covariance matrix.

    If the correlation matrix is not symmetric positive definite (SDP),
    the matrix is projected onto the SDP manifold and returned (together
    with a warning). The algorithm is according to Higham (2000)

    Args:
        df_correlations (DataFrame): correlation coefficients where
            columns and index are both parameter names. All parameter
            names in keys muvalst also exist in index and vice versa.

    Returns:
        covariance matrix
    """

    corr_matrix = numpy.array(df_correlations.values)

    # Assume upper triangular is empty, fill it:
    i_upper = numpy.triu_indices(len(df_correlations.columns), 1)
    corr_matrix[i_upper] = corr_matrix.T[i_upper]

    # Project to nearest symmetric positive definite matrix
    corr_matrix = _nearest_positive_definite(corr_matrix)
    # Previously negative eigenvalues are now close to zero,
    # but might still be negative, that can be ignored

    # Support unity standard devistions
    if not stddevs:
        stddevs = len(corr_matrix) * [1]

    # Now generate the covariance matrix
    dim = len(stddevs)
    diag = numpy.identity(dim)
    diag[range(dim), range(dim)] = stddevs
    cov_matrix = numpy.dot(diag, corr_matrix)
    cov_matrix = numpy.dot(cov_matrix, diag)

    return cov_matrix


def _nearest_positive_definite(a_mat):
    """Implementation taken from:
    https://stackoverflow.com/questions/43238173/
    python-convert-matrix-to-positive-semi-definite/43244194#43244194
    """

    b_mat = (a_mat + a_mat.T) / 2
    _, s_mat, v_mat = la.svd(b_mat)

    h_mat = numpy.dot(v_mat.T, numpy.dot(numpy.diag(s_mat), v_mat))

    a2_mat = (b_mat + h_mat) / 2

    a3_mat = (a2_mat + a2_mat.T) / 2

    if _is_positive_definite(a3_mat):
        return a3_mat

    spacing = numpy.spacing(la.norm(a_mat))
    identity = numpy.eye(a_mat.shape[0])
    kiter = 1
    while not _is_positive_definite(a3_mat):
        mineig = numpy.min(numpy.real(la.eigvals(a3_mat)))
        a3_mat += identity * (-mineig * kiter ** 2 + spacing)
        kiter += 1

    return a3_mat


def _is_positive_definite(b_mat):
    """Returns true when input is positive-definite, via Cholesky"""
    try:
        _ = la.cholesky(b_mat)
        return True
    except la.LinAlgError:
        return False
