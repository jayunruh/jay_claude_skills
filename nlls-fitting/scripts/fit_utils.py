"""Reusable pieces of the NLLS fitting workflow: an example fit function and
the Monte Carlo error-estimation routine. Import these, or copy/adapt the
pattern for a different model function.
"""
import numpy as np
import scipy.optimize as so


def double_gaussian(xvals, *params):
    """Example fit function: offset + two Gaussian peaks.

    params order: b, a1, xc1, s1, a2, xc2, s2
    (offset, amp1, center1, sigma1, amp2, center2, sigma2)
    """
    b, a1, xc1, s1, a2, xc2, s2 = params
    peak1 = a1 * np.exp(-(xc1 - xvals) ** 2 / (2.0 * s1 ** 2))
    peak2 = a2 * np.exp(-(xc2 - xvals) ** 2 / (2.0 * s2 ** 2))
    return b + peak1 + peak2


def monte_carlo_errors(xvals, yvals, fparams, fitfunc, bounds, niter=100):
    """Estimate parameter uncertainty by refitting many noisy realizations of
    the best fit rather than trusting the covariance-matrix approximation
    (which assumes linearity near the optimum and is often too small for
    NLLS problems with correlated parameters).

    Returns (errs, simfparams): per-parameter std dev, and the full array of
    simulated fit parameters (rows=iterations, cols=parameters) for anyone
    who wants to inspect the distributions directly (e.g. for skew or
    multimodality that a single std dev would hide).
    """
    fit = fitfunc(xvals, *fparams)
    resid_std = np.std(yvals - fit)
    simfparams = []
    for _ in range(niter):
        tsim = fit + np.random.normal(0.0, resid_std, size=len(fit))
        tparams, _ = so.curve_fit(fitfunc, xvals, tsim, p0=fparams, bounds=bounds, method='trf')
        simfparams.append(tparams)
    simfparams = np.array(simfparams)
    errs = simfparams.std(axis=0)
    return errs, simfparams
