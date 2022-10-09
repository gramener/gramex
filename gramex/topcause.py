import pandas as pd
from sklearn.base import BaseEstimator
import numpy as np
import warnings


class TopCause(BaseEstimator):
    '''TopCause finds the single largest action to improve a performance metric.

    Parameters
    ----------
    max_p : float
        maximum allowed probability of error (default: 0.05)
    percentile : float
        ignore high-performing outliers beyond this percentile (default: 0.95)
    min_weight : int
        minimum samples in a group. Drop groups with fewer (default: 3)

    Returns
    -------
    result_ : DataFrame
        rows = features evaluated
        columns:
            value: best value for this feature,
            gain: improvement in y if feature = value
            p: probability that this feature does not impact y
            type: how this feature's impact was calculated (e.g. `num` or `cat`)
    '''

    def __init__(
        self,
        max_p: float = 0.05,
        percentile: float = 0.95,
        min_weight: float = None,
    ):
        self.min_weight = min_weight
        self.max_p = max_p
        self.percentile = percentile

    def fit(self, X, y, sample_weight=None):  # noqa - capital X is a sklearn convention
        '''Returns the top causes of y from among X.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            n_samples = rows = number of observations.
            n_features = columns = number of drivers/causes.
        y : array-line of shape (n_samples)

        Returns
        -------
        self : object
            Returns the instance itself.
        '''
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)  # noqa: N806 X can be in uppercase
        if not isinstance(y, pd.Series):
            y = pd.Series(y)
        if X.shape[0] != y.shape[0]:
            raise ValueError(f'X has {X.shape[0]} rows, but y has {y.shape[0]} rows')

        # If values contain ±Inf treat it an NaN
        with pd.option_context('mode.use_inf_as_na', True):
            # If sample weights are not give, treat it as 1 for each row.
            # If sample weights are NaN, treat it as 0.
            if sample_weight is None:
                sample_weight = y.notnull().astype(int)
                # If no weights are specified, each category must have at least 3 rows
                min_weight = 3 if self.min_weight is None else self.min_weight
            elif not isinstance(sample_weight, pd.Series):
                sample_weight = pd.Series(sample_weight)
            sample_weight.fillna(0)

            # Calculate summary stats
            n = sample_weight.sum()
            weighted_y = y * sample_weight
            mean = weighted_y.sum() / n
            var = ((y - mean) ** 2 * sample_weight).sum() / n

            # Calculate impact for every column consistently
            results = {}
            for column, series in X.items():
                # Ignore columns identical to y
                if (series == y).all():
                    warnings.warn(f'column {column}: skipped. Identical to y')

                # Process column as NUMERIC, ORDERED CATEGORICAL or CATEGORICAL based on dtype
                # https://numpy.org/doc/stable/reference/generated/numpy.dtype.kind.html
                kind = series.dtype.kind

                # By default, assume that this column can't impact y
                result = results[column] = {
                    'value': np.nan,
                    'gain': np.nan,
                    'p': 1.0,
                    'type': kind,
                }

                # ORDERED CATEGORICAL if kind is signed or unsigned int
                # TODO: Currently, it's treated as numeric. Fix this based # of distinct ints.
                if kind in 'iu':
                    series = series.astype(float)
                    kind = 'f'

                # NUMERIC if kind is float
                if kind in 'f':
                    # Drop missing values, pairwise
                    pair = pd.DataFrame({'values': series, 'weight': sample_weight, 'y': y})
                    pair.dropna(inplace=True)

                    # Run linear regression to see if y increases/decreases with column
                    # TODO: use weighted regression
                    from scipy.stats import linregress

                    reg = linregress(pair['values'], pair['y'])

                    # If slope is +ve, pick value at the 95th percentile
                    # If slope is -ve, pick value at the 5th percentile
                    pair = pair.sort_values('values', ascending=True)
                    top = np.interp(
                        self.percentile if reg.slope >= 0 else 1 - self.percentile,
                        pair['weight'].cumsum() / pair['weight'].sum(),
                        pair['values'],
                    )

                    # Predict the gain based on linear regression
                    gain = reg.slope * top + reg.intercept - mean
                    if gain > 0:
                        result.update(value=top, gain=gain, p=reg.pvalue, type='num')

                # CATEGORICAL if kind is boolean, object, str or unicode
                elif kind in 'bOSU':
                    # Group into a DataFrame with 3 columns {value, weight, mean}
                    #   value: Each row has every unique value in the column
                    #   weight: Sum of sample_weights in each group
                    #   mean: mean(y) in each group, weighted by sample_weights
                    group = (
                        pd.DataFrame(
                            {'values': series, 'weight': sample_weight, 'weighted_y': weighted_y}
                        )
                        .dropna()
                        .groupby('values', sort=False)
                        .sum()
                    )
                    group['mean'] = group['weighted_y'] / group['weight']

                    # Pick the groups with highest mean(y), at >=95th percentile (or whatever).
                    # Ensure each group has at least min_weight samples.
                    group.sort_values('mean', inplace=True, ascending=True)
                    best_values = group.dropna(subset=['mean'])[
                        (group['weight'].cumsum() / group['weight'].sum() >= self.percentile)
                        & (group['weight'] >= min_weight)
                    ]

                    # If there's at least 1 group over 95th percentile with enough weights...
                    if len(best_values):
                        # X[series == top] is the largest group (by weights) above the 95th pc
                        top = best_values.sort_values('weight').iloc[-1]
                        gain = top['mean'] - mean
                        # Only consider positive gains
                        if gain > 0:
                            # Calculate p value using Welch test: scipy.stats.mstats.ttest_ind()
                            # https://en.wikipedia.org/wiki/Welch%27s_t-test
                            # github.com/scipy/scipy/blob/v1.5.4/scipy/stats/mstats_basic.py
                            subset = series == top.name
                            subseries = y[subset]
                            submean, subn = subseries.mean(), sample_weight[subset].sum()
                            with np.errstate(divide='ignore', invalid='ignore'):
                                diff = subseries - submean
                                vn1 = (diff**2 * sample_weight[subset]).sum() / subn
                                vn2 = var / n
                                df = (vn1 + vn2) ** 2 / (
                                    vn1**2 / (subn - 1) + vn2**2 / (n - 1)
                                )
                            df = 1 if np.isnan(df) else df
                            with np.errstate(divide='ignore', invalid='ignore'):
                                t = gain / (vn1 + vn2) ** 0.5
                            import scipy.special as special

                            p = special.betainc(0.5 * df, 0.5, df / (df + t * t))
                            # Update the result
                            result.update(value=top.name, gain=gain, p=p, type='cat')
                # WARN if kind is complex, timestamp, datetime, etc
                else:
                    warnings.warn(f'column {column}: unknown type {kind}')

            results = pd.DataFrame(results).T
            results.loc[results['p'] > self.max_p, ('value', 'gain')] = np.nan
            self.result_ = results.sort_values('gain', ascending=False)

        return self
