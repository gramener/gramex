import pandas as pd
import numpy as np
from gramex.config import app_log
from statsmodels import api as sm
from sklearn.metrics import mean_absolute_error


class SARIMAX(object):

    def __init__(self, order=(1, 0, 0), **kwargs):
        self.stl_kwargs = kwargs.pop('stl', False)
        self.params = kwargs

    def _timestamp_data(self, data, index_col):
        if data.index.name != index_col:
            data.set_index(index_col, verify_integrity=True, inplace=True)
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        return data

    def _get_stl(self, endog):
        if not self.stl_kwargs:
            return endog
        stl_components = self.stl_kwargs.get('components', [])
        if stl_components and (not set(stl_components) < {'seasonal', 'trend', 'resid'}):
            app_log.warning(f'Invalid STL components {stl_components}. Ignoring STL.')
            return endog
        kwargs = self.stl_kwargs.get('kwargs', {})

        app_log.critical(endog.index.freq)
        app_log.critical(endog.index.dtype)
        decomposed = sm.tsa.STL(endog, **kwargs).fit()
        result = np.zeros_like(endog)
        for comp in stl_components:
            result += getattr(decomposed, comp)
        return pd.Series(result, index=endog.index)

    def fit(self, X, y=None, index_col=None, target_col=None):
        """Only a dataframe is accepted. Index and target columns are both expected to be in it."""
        params = self.params.copy()
        if y is None:
            y = X[target_col]
            X = X.drop([target_col], axis=1)
        endog = y
        exog = X.drop([target_col], axis=1) if target_col in X else X
        params["exog"] = exog
        endog = self._timestamp_data(endog, index_col)
        endog.index.freq = self.params.pop("freq", pd.infer_freq(endog.index))
        endog = self._get_stl(endog)
        exog.index = endog.index
        missing = self.params.pop("missing", "drop")
        self.model = sm.tsa.SARIMAX(endog, missing=missing, **params)
        self.res = self.model.fit()
        return self.res.summary().as_html()

    def predict(self, data, index_col=None, start=None, end=None, target_col=None, **kwargs):
        data = self._timestamp_data(data, index_col)
        start = data.index.min() if start is None else start
        end = data.index.max() if end is None else end
        exog = data
        if target_col in data:
            exog = data.drop(target_col, axis=1)
        return self.res.predict(start, end, exog=exog, **kwargs)

    def score(self, data, y_pred, score_col):
        y_true = data[score_col].values
        y_true, y_pred = (
            pd.DataFrame({"y_true": y_true, "y_pred": y_pred.values}).dropna().values.T
        )
        return mean_absolute_error(y_true, y_pred)

    def forecast(self, *args):
        method = getattr(self.res, "forecast", False)
        if not method:
            raise NotImplementedError
        return method(*args)

    def get_params(self):
        return self.params
