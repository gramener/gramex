import pandas as pd
import numpy as np
import joblib
from gramex.config import app_log
from gramex import cache
from statsmodels import api as sm
from statsmodels.tsa.statespace.sarimax import SARIMAXResultsWrapper
from sklearn.metrics import mean_absolute_error
from gramex.ml_api import AbstractModel


class StatsModel(AbstractModel):

    @classmethod
    def from_disk(cls, store, klass=None, **kwargs):
        model = cache.open(store.model_path, joblib.load)
        return cls(model, store, params={})

    def __init__(self, mclass, store, *args, **kwargs):
        self.stl_kwargs = kwargs.pop("stl", False)
        if isinstance(mclass, SARIMAXResultsWrapper):
            self.res = mclass
        self.mclass = mclass
        self.params = kwargs
        self.store = store

    def _timestamp_data(self, data, index_col):
        if data.index.name != index_col:
            data.set_index(index_col, verify_integrity=True, inplace=True)
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        return data

    def _get_stl(self, endog):
        if not self.stl_kwargs:
            return endog
        stl_components = self.stl_kwargs.get("components", [])
        if stl_components and (
            not set(stl_components) < {"seasonal", "trend", "resid"}
        ):
            app_log.warning(f"Invalid STL components {stl_components}. Ignoring STL.")
            return endog
        kwargs = self.stl_kwargs.get("kwargs", {})

        decomposed = sm.tsa.STL(endog, **kwargs).fit()
        result = np.zeros_like(endog)
        for comp in stl_components:
            result += getattr(decomposed, comp)
        return pd.Series(result, index=endog.index)

    def _init_fit(self, name=''):
        data = self.store.load_data()
        if not len(data):
            return
        data = self._filtercols(data)
        data = self._filterrows(data)
        target = self.store.load('target_col')
        X = data.drop([target], axis=1)
        y = data[target]
        self.fit(X, y, self.store.model_path, name)

    def fit(
        self, data, model_path=None, name=None, index_col=None, target_col=None,
        **kwargs
    ):
        """Only a dataframe is accepted. Index and target columns are both expected to be in it."""
        if index_col is None:
            index_col = self.store.load('index_col')
        if target_col is None:
            target_col = self.store.load('target_col')
        params = self.params.copy()
        data = self._timestamp_data(data, index_col)
        X = data.drop([target_col], axis=1)
        y = data[target_col]
        endog = y
        exog = X.drop([target_col], axis=1) if target_col in X else X
        params["exog"] = exog
        endog.index.freq = self.params.pop("freq", pd.infer_freq(endog.index))
        endog = self._get_stl(endog)
        exog.index = endog.index
        missing = self.params.pop("missing", "drop")
        self.model = self.mclass(endog, missing=missing, **params)
        self.res = self.model.fit()
        self.res.save(model_path)
        return self.res.summary().as_html()

    def predict(
        self, data, index_col=None, start=None, end=None, target_col=None, **kwargs
    ):
        data = self._timestamp_data(data, index_col)
        start = data.index.min() if start is None else start
        end = data.index.max() if end is None else end
        exog = data
        if target_col in data:
            exog = data.drop(target_col, axis=1)
        return self.res.predict(start, end, exog=exog, **kwargs)

    def score(self, data, target_col, metric='', **kwargs):
        """Metric is ignored, only included for compatibility."""
        X = data.drop([target_col], axis=1)
        y_true = data[target_col]
        y_pred = self.res.predict(start=X.index.min(), end=X.index.max(), exog=X)
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

    def get_attributes(self):
        result = getattr(self, "res", False)
        if not result:
            return {}
        return result.summary().as_html()
