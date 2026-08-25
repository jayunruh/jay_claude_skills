"""Simulate a noisy double-Gaussian curve for users who have no data of their own yet.

Run directly to write simulated_curve.csv into the current directory:
    pixi run python simulate_data.py
Or import simDoubleGauss() to generate data in-process.
"""
import numpy as np
import pandas as pd


def simDoubleGauss(xvals=None, paramdict=None, noise_std=1.0, seed=None):
    """Simulate a double Gaussian curve with additive Gaussian noise.

    paramdict keys: b (offset), a1/xc1/s1 (amp/center/sigma of peak 1),
    a2/xc2/s2 (amp/center/sigma of peak 2).
    """
    if paramdict is None:
        paramdict = {'b': 2.0, 'a1': 10.0, 'xc1': 30.0, 's1': 10.0,
                     'a2': 15.0, 'xc2': 60.0, 's2': 20.0}
    simx = xvals if xvals is not None else np.arange(100)
    sim = (paramdict['b']
           + paramdict['a1'] * np.exp(-(paramdict['xc1'] - simx) ** 2 / (2.0 * paramdict['s1'] ** 2))
           + paramdict['a2'] * np.exp(-(paramdict['xc2'] - simx) ** 2 / (2.0 * paramdict['s2'] ** 2)))
    rng = np.random.default_rng(seed)
    sim = sim + rng.normal(0.0, noise_std, size=len(simx))
    return simx, sim


if __name__ == '__main__':
    simx, simvals = simDoubleGauss()
    pd.DataFrame({'x': simx, 'y': simvals}).to_csv('simulated_curve.csv', index=False)
    print('Wrote simulated_curve.csv with', len(simx), 'points')
