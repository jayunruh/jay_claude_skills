"""End-to-end worked example of the full NLLS fitting workflow, adapted from
fitting_tutorial.ipynb. Run with:
    pixi run python example_double_gaussian.py
This simulates data, fits it, reports errors two ways, and saves the plots as
PNGs (fit_plot.png, mc_histograms.png) instead of opening an interactive
window, since this is typically run from Claude rather than a live Python
session. Use it as a template: swap in real data and a different fitfunc as
needed.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.optimize as so

from simulate_data import simDoubleGauss
from fit_utils import double_gaussian, monte_carlo_errors

PARAM_NAMES = ['b', 'a1', 'xc1', 's1', 'a2', 'xc2', 's2']


def main():
    # Step 0: get data (here simulated; swap for pd.read_csv(...) on real data)
    simx, simvals = simDoubleGauss(seed=0)

    # Step 1: guess starting parameters and bounds
    # xc/sigma must be estimated by eye from a plot of the data; b/amp can be
    # estimated from summary statistics.
    gmin = simvals.min()
    gamp = simvals.max() - gmin
    gparams = [gmin, gamp, 35.0, 10.0, gamp, 60.0, 10.0]
    lower = [gparams[0] - 0.25 * gamp, 0.2 * gamp, gparams[2] - gparams[3], 0.2 * gparams[3],
             0.2 * gamp, gparams[5] - gparams[6], 0.2 * gparams[6]]
    upper = [gparams[0] + 0.25 * gamp, 3.0 * gamp, gparams[2] + gparams[3], 3.0 * gparams[3],
             3.0 * gamp, gparams[5] + gparams[6], 3.0 * gparams[6]]

    # Step 2: run the fit
    fparams, fcov = so.curve_fit(double_gaussian, simx, simvals, p0=gparams,
                                  bounds=(lower, upper), method='trf')
    cov_errs = np.sqrt(np.diag(fcov))
    fit = double_gaussian(simx, *fparams)
    rchi2 = ((simvals - fit) ** 2).sum() / (len(simvals) - len(gparams))

    print('Fit parameters:', dict(zip(PARAM_NAMES, fparams)))
    print('Covariance-based errors:', dict(zip(PARAM_NAMES, cov_errs)))
    print('Reduced chi-squared:', rchi2)

    plt.figure()
    plt.plot(simx, simvals, 'b.', label='data')
    plt.plot(simx, fit, 'r-', label='fit')
    plt.xlabel('x')
    plt.ylabel('y')
    plt.legend()
    plt.title('Fit result')
    plt.savefig('fit_plot.png', dpi=120)

    # Step 3: Monte Carlo error analysis (more robust than covariance errors,
    # especially when parameters are correlated or bounds are active)
    mc_errs, mc_params = monte_carlo_errors(simx, simvals, fparams, double_gaussian,
                                             bounds=(lower, upper), niter=200)
    print('Monte Carlo errors:', dict(zip(PARAM_NAMES, mc_errs)))

    results = pd.DataFrame({
        'parameter': PARAM_NAMES,
        'value': fparams,
        'cov_error': cov_errs,
        'mc_error': mc_errs,
    })
    print(results)
    results.to_csv('fit_results.csv', index=False)

    fig, axes = plt.subplots(2, 4, figsize=(14, 6))
    for i, name in enumerate(PARAM_NAMES):
        ax = axes.flat[i]
        ax.hist(mc_params[:, i], bins=30)
        ax.set_title(name)
    fig.suptitle('Monte Carlo parameter distributions')
    fig.tight_layout()
    fig.savefig('mc_histograms.png', dpi=120)
    print('Saved fit_plot.png, mc_histograms.png, and fit_results.csv')


if __name__ == '__main__':
    main()
