import pandas as pd
from statsmodels import api as sm
from gramex.config import app_log


class BaseModel(object):
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

    def fit(self, X, y):
        y.index.freq = self.params.pop('freq', pd.infer_freq(y.index))
        self.res = self.mclass(y, X, **self.params).fit()

    def predict(self, start, end, **kwargs):
        return self.res.predict(start, end, **kwargs)

    def forecast(self, *args):
        method = getattr(self.res, 'forecast', False)
        if not method:
            raise NotImplementedError
        return method(*args)

    def get_params(self):
        return self.params


class AutoReg(BaseModel):
    mclass = sm.tsa.AutoReg
    is_univariate = True

    def __init__(self, lags: int, missing="drop", **kwargs):
        self.params = {'lags': lags, 'missing': missing}
        self.params.update(kwargs)

    def fit(self, X, y, target_col=None):
        if self.is_univariate:
            y = self._coerce_1d(y, target_col)
        y.index.freq = self.params.pop('freq', pd.infer_freq(y.index))
        missing = self.params.pop('missing', 'drop')
        self.res = self.mclass(y, missing=missing, **self.params).fit()
        return self.res


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
