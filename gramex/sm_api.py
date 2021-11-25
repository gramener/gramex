import pandas as pd
from gramex.config import app_log
from statsmodels import api as sm
from sklearn.metrics import mean_absolute_error


class BaseStatsModel(object):
    mclass = None

    def __init__(self, **kwargs):
        self.params = kwargs

    def _coerce_1d(self, y, target_col=None):
        if isinstance(y, pd.DataFrame) and len(y.columns) > 1:
            app_log.warning('Autoregressive models support only univariate data.')
            if target_col is None:
                raise ValueError('Please specify a target column.')
            app_log.warning(f'Looking for target column {target_col} in dataset.')
            y = y[target_col]
        return y.squeeze()

    def _timestamp_data(self, data, index_col):
        if data.index.name != index_col:
            data[index_col] = pd.to_datetime(data[index_col])
            return data.set_index(index_col, verify_integrity=True)
        return data

    def predict(self, data, start, end, index_col, target_col=None, **kwargs):
        if not self.is_univariate:
            data = self._timestamp_data(data, index_col)
            exog = data
            if target_col in data:
                exog = data.drop(target_col, axis=1)
            return self.res.predict(start, end, exog=exog, **kwargs)
        return self.res.predict(start, end, **kwargs)

    def score(self, data, y_pred, score_col):
        y_true = data[score_col]
        y_true, y_pred = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred}).dropna().values.T
        return mean_absolute_error(y_true, y_pred)

    def forecast(self, *args):
        method = getattr(self.res, 'forecast', False)
        if not method:
            raise NotImplementedError
        return method(*args)

    def get_params(self):
        return self.params


class AutoReg(BaseStatsModel):
    mclass = sm.tsa.AutoReg
    is_univariate = True

    def __init__(self, lags: int, missing="drop", **kwargs):
        self.params = {'lags': lags, 'missing': missing}
        self.params.update(kwargs)

    def fit(self, X, y, index_col=None, target_col=None):
        if self.is_univariate:
            y = self._coerce_1d(y, target_col)
        y = self._timestamp_data(y, index_col)
        y.index.freq = self.params.pop('freq', pd.infer_freq(y.index))
        missing = self.params.pop('missing', 'drop')
        self.model = self.mclass(y, missing=missing, **self.params)
        self.res = self.model.fit()
        return self.res.summary().as_html()


class ARIMA(AutoReg):
    mclass = sm.tsa.ARIMA

    def __init__(self, order=(1, 0, 0), **kwargs):
        self.params = {'order': order}
        self.params.update(kwargs)


class SARIMAX(ARIMA):
    mclass = sm.tsa.SARIMAX
    is_univariate = False


class ARDL(AutoReg):
    mclass = sm.tsa.ARDL
    is_univariate = False
