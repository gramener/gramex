from collections import defaultdict
from inspect import getargspec
import json
import os
import warnings
from tempfile import gettempdir

import gramex
from gramex.config import app_log, variables
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND
from gramex.install import _mkdir
from gramex import cache
import joblib
import numpy as np
import pandas as pd
import pydoc
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from slugify import slugify
from tornado.gen import coroutine
from tornado.web import HTTPError

op = os.path
DATA_CACHE = defaultdict(dict)
SCORES = defaultdict(list)
MLCLASS_MODULES = [
    'sklearn.linear_model',
    'sklearn.tree',
    'sklearn.ensemble',
    'sklearn.svm',
    'sklearn.neighbors',
    'sklearn.neural_network',
    'sklearn.naive_bayes',
    'statsmodels.api',
    'statsmodels.tsa.api',
    'tensorflow.keras.applications'
]


def search_modelclass(mclass):
    for module in MLCLASS_MODULES:
        cls = pydoc.locate(f'{module}.{mclass}')
        if cls:
            return cls
    # Search with the literal path
    cls = pydoc.locate(mclass)
    if cls:
        return cls
    msg = f'Model {mclass} not found. Please provide a full Python path.'
    raise HTTPError(NOT_FOUND, reason=msg)


def _serialize_prediction(obj):
    # Serialize a list or an array or a tensor
    if isinstance(obj, np.ndarray):
        obj = obj.tolist()
    return json.dumps(obj, indent=4)


def is_categorical(s, num_treshold=0.66):
    """Check if a series contains a categorical variable.

    Parameters
    ----------
    s : pd.Series

    Returns
    -------
    bool:
        Whether the series is categorical.
    """
    if pd.api.types.is_numeric_dtype(s):
        if s.nunique() / s.shape[0] <= num_treshold:
            return True
        return False
    return True


class MLHandler(FormHandler):
    @classmethod
    def setup(cls, path='', model_class=None, model_params=None, **kwargs):
        super(MLHandler, cls).setup(**kwargs)
        if not model_params:
            model_params = {}
        if path:
            cls.model_path = path
        else:
            mname = slugify(cls.name) + '.pkl'
            mpath = op.join(variables['GRAMEXDATA'], 'apps', 'mlhandler')
            _mkdir(mpath)
            cls.model_path = op.join(mpath, mname)
        if op.isfile(path):
            cls.model = cache.open(path, joblib.load)
            if model_class:
                mclass = search_modelclass(model_class)
                if not isinstance(cls.model, mclass):
                    import textwrap
                    msg = f'''
                    The model present at {cls.model_path} is not a {model_class}.
                    Overwriting it.'''
                    warnings.warn(textwrap.dedent(msg))
                    cls.model = mclass(**model_params)
        elif model_class:
            mclass = search_modelclass(model_class)
            cls.model = mclass(**model_params)
        else:
            cls.model = None
        if cls.model:
            joblib.dump(cls.model, cls.model_path)

    def _fit(self, data):
        data = self._transform(data)
        target = self.kwargs.get('_target_col', self.get_arg('_target_col'))
        target = data.pop(target)
        DATA_CACHE[self.name]['input'] = data.columns.tolist()
        DATA_CACHE[self.name]['target'] = target.name
        DATA_CACHE[self.name]['train_shape'] = data.shape
        self.pipeline = self._assemble_pipeline(data)
        self.pipeline.fit(data, target)
        joblib.dump(self.pipeline, self.model_path)
        if not self.get_arg('_score', False):
            try:
                score = self.pipeline.score(data, target)
            except AttributeError:
                score = f"A model of type {type(self.model)} does not have a score method."
            SCORES[self.model_path].append(score)
            return SCORES[self.model_path][-1]

    def _predict(self, data):
        data = self._transform(data)
        return self.model.predict(data)

    def _coerce_model_params(self, mclass=None, params=None):
        if self.model:
            model_params = self.model.get_params()
        else:
            spec = getargspec(mclass)
            m_args = spec.args
            m_args.remove('self')
            m_defaults = spec.defaults
            model_params = {k: v for k, v in zip(m_args, m_defaults)}
        if not params:
            new_params = {k: v[0] for k, v in self.args.items() if k in model_params}
        else:
            new_params = params
        param_types = {}
        for k, v in model_params.items():
            if v is None:
                param_types[k] = str
            else:
                param_types[k] = type(v)
        return {k: param_types[k](v) for k, v in new_params.items()}

    def _filter_model_params(self, mclass):
        spec = [c for c in getargspec(mclass).args if c != 'self']
        return {k: v[0] for k, v in self.args.items() if k in spec}

    def _assemble_pipeline(self, data):
        if json.loads(self.get_arg('_pipeline', 'false')):
            categoricals = [c for c in data if is_categorical(data[c])]
            numericals = [c for c in data if pd.api.types.is_numeric_dtype(data[c])]
            ct = ColumnTransformer([('ohe', OneHotEncoder(sparse=False), categoricals),
                                    ('scaler', StandardScaler(), numericals)])
            return Pipeline([('transform', ct), (self.model.__class__.__name__, self.model)])
        return self.model

    def _deduplicate(self, df):
        dedup = json.loads(self.get_arg('_deduplicate', 'true'))
        if dedup:
            if isinstance(dedup, list):
                subset = dedup
            else:
                subset = None
            return df.drop_duplicates(subset=subset)
        return df

    def _dropna(self, df):
        dropna = json.loads(self.get_arg('_dropna', 'true'))
        if dropna:
            if isinstance(dropna, list):
                subset = dropna
            else:
                subset = None
            return df.dropna(subset=subset)
        return df

    def _filtercols(self, df):
        target_col = self.kwargs.get('_target_col', self.get_arg('_target_col', False))
        if target_col:
            target = df.pop(target_col)
        include = self.args.get('_include', [])
        exclude = self.args.get('_exclude', [])
        if len(include) > 0:
            df = df[include]
        if len(exclude) > 0:
            df.drop(exclude, axis=1, inplace=True)
        if target_col:
            df[target_col] = target
        return df

    def _transform(self, df=None):
        if df is None:
            df = DATA_CACHE[self.name]['data'].copy()
        df = self._deduplicate(df)
        df = self._dropna(df)
        df = self._filtercols(df)
        return df

    @property
    def _data_cachedir(self):
        cache_dir = op.join(gettempdir(), self.session['id'])
        _mkdir(cache_dir)
        return cache_dir

    @coroutine
    def get(self, *path_args, **path_kwargs):
        if self.model is None:
            self.model = cache.open(self.model_path, joblib.load)
        if self.args.get('_cache', False):
            out = {k: v for k, v in DATA_CACHE[self.name].items() if k != 'data'}
            out.update({'data': DATA_CACHE[self.name]['data'].to_dict(orient='records')})
            self.write(json.dumps(out, indent=4))
        elif self.args.get('_model', False):
            out = {'params': self.model.get_params()}
            out.update({k: v for k, v in DATA_CACHE[self.name].items() if k != 'data'})
            if len(SCORES[self.model_path]) > 0:
                out['score'] = SCORES[self.model_path][-1]
            out['model'] = self.model.__class__.__name__
            self.write(json.dumps(out, indent=4))
        elif self.args.get('_download', False):
            self.set_header('Content-Type', 'application/octet-strem')
            self.set_header('Content-Disposition',
                            f'attachment; filename={op.basename(self.model_path)}')
            return open(self.model_path, 'rb').read()
        else:
            try:
                data = pd.DataFrame(self.args)
            except Exception as err:
                app_log.debug(err.msg)
            prediction = yield gramex.service.threadpool.submit(self._predict, data)
            self.write(_serialize_prediction(prediction))
        super(MLHandler, self).get(*path_args, **path_kwargs)

    def _parse_data(self, _cache=True):
        # First look in self.request.files
        if len(self.request.files) > 0:
            dfs = []
            for _, files in self.request.files.items():
                for f in files:
                    outpath = op.join(self._data_cachedir, f['filename'])
                    with open(outpath, 'wb') as fout:
                        fout.write(f['body'])
                    if outpath.endswith('.json'):
                        xdf = cache.open(outpath, pd.read_json)
                    else:
                        xdf = cache.open(outpath)
                    dfs.append(xdf)
            data = pd.concat(dfs, axis=0)
        # Otherwise look in request.body
        else:
            try:
                data = pd.read_json(self.request.body.decode('utf8'))
            except ValueError:
                data = DATA_CACHE.get(self.name, {}).get('data', [])
                _cache = False
        if _cache:
            orgdf = DATA_CACHE.get(self.name, {}).get('data', [])
            if len(orgdf):
                data = pd.concat((orgdf, data), axis=0)
            DATA_CACHE[self.name]['data'] = data
        return data

    @coroutine
    def post(self, *path_args, **path_kwargs):
        if self.get_arg('_retrain', False):
            data = self._parse_data()
            score = yield gramex.service.threadpool.submit(self._fit, data)
            self.write(json.dumps(dict(score=score), indent=4))
        else:
            data = self._parse_data(False)
            prediction = yield gramex.service.threadpool.submit(self._predict, data)
            self.write(_serialize_prediction(prediction))
        super(MLHandler, self).get(*path_args, **path_kwargs)

    @coroutine
    def put(self, *path_args, **path_kwargs):
        # TODO: If we change the model class, GET ?_model does not return the new one
        mclass = self.args.pop('class')[0]
        _retrain = self.args.pop('_retrain', False)
        if not op.isfile(self.model_path):
            mclass = search_modelclass(mclass)
            mparams = self._filter_model_params(mclass)
            mparams = self._coerce_model_params(mclass, mparams)
            self.model = mclass(**mparams)
        else:
            self.model = cache.open(self.model_path, joblib.load)
            mclass = search_modelclass(mclass)
            model_kwargs = self._coerce_model_params()
            if not isinstance(self.model, mclass):
                self.model = mclass(**model_kwargs)
            else:
                [setattr(self.model, k, v) for k, v in model_kwargs.items()]
        joblib.dump(self.model, self.model_path)
        out = {'model': self.model.__class__.__name__,
               'params': self.model.get_params()}
        if _retrain:
            data = self._parse_data()
            score = yield gramex.service.threadpool.submit(self._fit, data)
            out.update({'score': score})
        self.write(json.dumps(out, indent=4))

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        if self.args.get('_cache', False):
            if self.name in DATA_CACHE:
                del DATA_CACHE[self.name]
        else:
            if not op.isfile(self.model_path):
                raise HTTPError(NOT_FOUND, reason=f'Model {self.model_path} does not exist.')
            os.remove(self.model_path)
