---
name: nlls-fitting
description: Guides non-linear least squares (NLLS) curve fitting in Python with scipy.optimize.curve_fit — defining a model/fit function, choosing initial parameter guesses and bounds, running the fit, and estimating parameter uncertainty both from the covariance matrix and via Monte Carlo resampling of residuals. Use this skill whenever the user wants to fit a curve or model to data, mentions curve_fit, non-linear least squares, NLLS, peak fitting (e.g. Gaussian, Lorentzian, exponential, sigmoidal peaks/curves), extracting parameters and error bars from a dataset, chi-squared/reduced chi-squared, or Monte Carlo uncertainty analysis on fit parameters — even if they don't explicitly say "scipy" or name this skill.
---

# Non-linear least squares fitting

Workflow for fitting a parametric model to (x, y) data with `scipy.optimize.curve_fit`
and getting trustworthy error bars on the fitted parameters. The same four steps apply
regardless of the model — a double Gaussian is used as the running example below (and
in the bundled scripts), but swap in whatever functional form the data calls for.

Why this matters: `curve_fit`'s default covariance-based errors assume the fit is
locally linear and unconstrained near the optimum. That assumption breaks down when
parameters are correlated or bounds are active, which is common in practice — so this
workflow always follows up covariance errors with a Monte Carlo check (Step 3).

## Step 0: Environment setup

Use pixi so the fitting environment is reproducible. Copy [assets/pixi.toml](assets/pixi.toml)
into the user's working directory (create one if they don't have one yet), then:

```bash
pixi install
```

This pins python, numpy, scipy, matplotlib, and pandas. Run all commands in this
workflow with `pixi run <command>` (per this user's global Python conventions) — never
`pip install` directly into the environment.

If the user has their own data, load it with pandas and confirm it has clear x and y
columns before proceeding. If they don't have data yet (e.g. they just want to try the
workflow, or test a fit function before applying it to real data), simulate a noisy
double-Gaussian curve with [scripts/simulate_data.py](scripts/simulate_data.py):

```python
from simulate_data import simDoubleGauss
simx, simvals = simDoubleGauss()  # override paramdict= for different peak shapes
```

## Step 1: Define the fit function, initial guesses, and bounds

Write the model as a function of `(xvals, *params)` — `curve_fit` requires positional
params, not a dict, but naming them internally makes the function readable:

```python
import numpy as np

def fitfunc(xvals, *params):
    b, a1, xc1, s1, a2, xc2, s2 = params  # offset, amp1, center1, sigma1, amp2, center2, sigma2
    peak1 = a1 * np.exp(-(xc1 - xvals) ** 2 / (2.0 * s1 ** 2))
    peak2 = a2 * np.exp(-(xc2 - xvals) ** 2 / (2.0 * s2 ** 2))
    return b + peak1 + peak2
```

[scripts/fit_utils.py](scripts/fit_utils.py) has this as `double_gaussian` ready to import.

**Initial guesses are the hard part** and are highly dependent on the model and dataset
— there's no universal recipe. A practical approach:

1. Estimate what you can from simple statistics (e.g. offset ≈ `y.min()`, amplitude ≈
   `y.max() - y.min()`).
2. Estimate the rest (peak centers, widths, rate constants, etc.) by eye from a plot of
   the data — plot the data with the guessed-parameter curve overlaid and iterate with
   the user until it visually tracks the data reasonably well. A bad guess is the most
   common reason `curve_fit` fails to converge or gets stuck at a boundary.
3. If some parameters are especially hard to guess (e.g. a peak center in noisy data),
   consider a small grid search over just those parameters, scoring each candidate by
   sum-of-squared-residuals, before handing off to `curve_fit`.

Once guesses exist, derive bounds from them rather than guessing bounds independently —
this keeps the search space centered on something plausible. A common default is
1/3× the guess for the lower bound and 3× for the upper bound (adjust for parameters
that can be negative or that have known physical limits, e.g. a peak center probably
shouldn't roam far outside the x-range of the data).

## Step 2: Run the fit

```python
import scipy.optimize as so
import numpy as np

fparams, fcov = so.curve_fit(fitfunc, xvals, yvals, p0=guessparams,
                              bounds=(lower_lim, upper_lim), method='trf')
# sqrt of the diagonal of the covariance matrix = approximate standard errors
cov_errs = np.sqrt(np.diag(fcov))
fit = fitfunc(xvals, *fparams)
rchi2 = ((yvals - fit) ** 2).sum() / (len(yvals) - len(guessparams))
```

`method='trf'` (Trust Region Reflective) is used throughout because it natively
supports bounds — the other scipy methods either ignore bounds or require unbounded
problems.

Plot the data (points) with the fit overlaid (line) for visual validation regardless of
what the reduced chi-squared says — a good chi-squared with a visibly bad fit usually
means the noise model or the y-errors are misestimated, not that the fit is trustworthy.
Since this workflow typically runs from Claude rather than an interactive Python
session, use `plt.savefig(...)` and show the user the resulting image rather than
`plt.show()`, which has no effect outside an interactive session. Save fit parameters
and errors to a DataFrame (see Step 3 for the combined version with Monte Carlo errors).

## Step 3: Monte Carlo error analysis

The covariance-based `cov_errs` above are a linear approximation and are frequently too
small, especially when parameters trade off against each other (e.g. amplitude vs.
width) or a bound is active. To get a more realistic error estimate, simulate many
noisy realizations of the best fit (using the residual standard deviation as the noise
level) and refit each one — the spread of the refit results is the error estimate.

[scripts/fit_utils.py](scripts/fit_utils.py) provides `monte_carlo_errors`:

```python
from fit_utils import monte_carlo_errors

mc_errs, mc_params = monte_carlo_errors(xvals, yvals, fparams, fitfunc,
                                         bounds=(lower_lim, upper_lim), niter=100)
```

`mc_params` holds every simulated fit's parameters (shape `niter × n_params`) — worth
histogramming per parameter (see [scripts/example_double_gaussian.py](scripts/example_double_gaussian.py)
for the plotting pattern) since a skewed or bimodal distribution is a sign that a bound
is active or the model is not well-identified from this data, which a single std-dev
number would hide.

Increase `niter` (e.g. to 500-1000) when the user needs tighter confidence in the error
estimate itself, at the cost of runtime — each iteration is a full `curve_fit` call.

Combine both error estimates into one results table for the user:

```python
import pandas as pd

results = pd.DataFrame({'parameter': param_names, 'value': fparams,
                         'cov_error': cov_errs, 'mc_error': mc_errs})
```

## Full worked example

[scripts/example_double_gaussian.py](scripts/example_double_gaussian.py) runs Steps
0-3 end to end on simulated data — simulate, guess, fit, plot, Monte Carlo, save
results to CSV. Use it as a template to adapt: swap `simulate_data`/`double_gaussian`
for the user's actual data and model, and adjust the guess/bounds logic in Step 1 to
match the new parameters.
