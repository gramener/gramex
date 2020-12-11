from collections import defaultdict
from inspect import signature
import json
import os
from tempfile import gettempdir
from urllib.parse import parse_qs

import gramex
from gramex.config import app_log
from gramex import data as gdata
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND, BAD_REQUEST
from gramex.install import _mkdir
from gramex import cache
import joblib
import numpy as np
import pandas as pd
import pydoc
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils import estimator_html_repr
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
TRAINING_DEFAULTS = {
    'include': [],
    'exclude': [],
    'dropna': True,
    'deduplicate': True,
    'pipeline': True,
    'nums': [],
    'cats': [],
    'class': None,
    'target_col': None,
}


def _fit(model, x, y, path=None, name=None):
    getattr(model, 'partial_fit', model.fit)(x, y)
    if path:
        joblib.dump(model, path)
        app_log.info(f'{name}: Model saved at {path}.')
    return model


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


def is_categorical(s, num_treshold=0.1):
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
    def setup(cls, data=None, model=None, **kwargs):
        cls.template = kwargs.pop('template', True)
        super(MLHandler, cls).setup(**kwargs)
        if isinstance(data, str):
            data = cache.open(data)
        elif isinstance(data, dict):
            data = gdata.filter(**data)
        else:
            data = None
        if data is not None:
            cls.cache_data(data)

        # parse model kwargs
        if model is None:
            model = {}
        model_path = model.pop('path', '')
        if op.exists(model_path):  # If the pkl exists, load it
            cls.model = joblib.load(model_path)
            cls.model_path = model_path
            target_col = model.get('target_col', False)
            cls.set_opt('target_col', target_col)
        else:  # build the model
            params = cls._get_cached_params()
            if not params:
                params = model.get('params', {})
            mclass = cls.get_opt('class', model.get('class', False))
            if mclass:
                cls.model = search_modelclass(mclass)(**params)
            else:
                cls.model = None
            if model_path:  # if a path is specified, use to to store the model
                cls.model_path = model_path
            else:  # or create our own path
                cls.model_path = op.join(
                    gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler',
                    slugify(cls.name) + '.pkl')
                _mkdir(op.dirname(cls.model_path))

            # train the model
            target_col = model.get('target_col', False)
            if cls.model and not target_col:
                raise ValueError('Target column not defined.')
            cls.set_opt('target_col', target_col)

            if cls.model is not None:
                # filter columns
                data = cls._filtercols(data, **model)

                # filter rows
                data = cls._filterrows(data, **model)

                # assemble the pipeline
                if model.get('pipeline', True):
                    cls.model = cls._get_pipeline(data, **model)
            else:
                opts = cls.get_opt()
                if opts:
                    cls.model = cls._get_pipeline(data, **opts)

            # train the model
            if data is not None:
                target = data[target_col]
                train = data[[c for c in data if c != target_col]]
                if model.get('async', True):
                    gramex.service.threadpool.submit(
                        _fit, cls.model, train, target, cls.model_path, cls.name)
                else:
                    _fit(cls.model, train, target, cls.model_path, cls.name)

    @classmethod
    def _get_cached_params(cls):
        cache = DATA_CACHE[slugify(cls.name)].get('opts', {})
        return {k: v for k, v in cache.items() if k not in TRAINING_DEFAULTS.keys()}

    @classmethod
    def cache_data(cls, data):
        key = slugify(cls.name)
        orgdata = DATA_CACHE.get(key, {'data': []}).get('data')
        if orgdata and len(orgdata):
            if isinstance(orgdata, pd.DataFrame) and np.all(orgdata.columns == data.columns):
                data = pd.concat((orgdata, data), axis=0, ignore_index=True)
        DATA_CACHE[key]['data'] = data

    @classmethod
    def _filtercols(cls, data, **model_kwargs):
        include = cls.get_opt('include', model_kwargs.get('include', []))
        if include:
            data = data[include]
        exclude = cls.get_opt('exclude', model_kwargs.get('exclude', []))
        if exclude:
            data = data.drop(exclude, axis=1)
        cls.set_opt('include', include)
        cls.set_opt('exclude', exclude)
        return data

    @classmethod
    def _filterrows(cls, data, **model_kwargs):
        for method in 'dropna drop_duplicates'.split():
            action = model_kwargs.get(method, True)
            DATA_CACHE[slugify(cls.name)][action] = True
            if action:
                if isinstance(action, list):
                    subset = action
                else:
                    subset = None
                data = getattr(data, method)(subset=subset)
        return data

    @classmethod
    def _get_pipeline(cls, data, **model_kwargs):
        if data is not None:
            if not len(data):
                return None
        else:
            return None
        nums = set(model_kwargs.get('nums', []))
        cats = set(model_kwargs.get('cats', []))
        both = nums.intersection(cats)
        if len(both) > 0:
            raise HTTPError(
                BAD_REQUEST,
                reason=f"Columns {both} cannot be both numerical and categorical.")
        to_guess = set(data.columns.tolist()) - nums.union(cats)
        target_col = model_kwargs.get('target_col', False)
        if target_col:
            to_guess = to_guess - {target_col}
        categoricals = [c for c in to_guess if is_categorical(data[c])]
        for c in categoricals:
            to_guess.remove(c)
        numericals = [c for c in to_guess if pd.api.types.is_numeric_dtype(data[c])]
        categoricals += list(cats)
        numericals += list(nums)
        assert len(set(categoricals) & set(numericals)) == 0
        steps = []
        if categoricals:
            steps.append(('ohe', OneHotEncoder(sparse=False), categoricals))
        if numericals:
            steps.append(('scaler', StandardScaler(), numericals))
        ct = ColumnTransformer(steps)
        if isinstance(cls.model, Pipeline):
            for k, v in cls.model.named_steps.items():
                if k != 'transform':
                    break
            model = v
        elif isinstance(cls.model, BaseEstimator):
            model = cls.model
        elif cls.model is None:
            mclass = search_modelclass(cls.get_opt('class'))
            model = mclass(**cls._get_cached_params())
        return Pipeline([('transform', ct), (model.__class__.__name__, model)])

    @property
    def _data_cachedir(self):
        cache_dir = op.join(gettempdir(), self.session['id'])
        _mkdir(cache_dir)
        return cache_dir

    @classmethod
    def get_opt(cls, opt=None, default=None):
        if opt:
            return DATA_CACHE[slugify(cls.name)].get('opts', {}).get(opt, default)
        return DATA_CACHE[slugify(cls.name)].get('opts', {})

    @classmethod
    def set_opt(cls, opt, value):
        cache = DATA_CACHE[slugify(cls.name)]
        if 'opts' not in cache:
            cache['opts'] = {}
        cache['opts'][opt] = value

    def _transform(self, data, **kwargs):
        cfg = DATA_CACHE[slugify(self.name)]
        for col in data:
            data[col] = data[col].astype(cfg['data'][col].dtype)
        # transform columns
        include = cfg.get('include', kwargs.get('include', []))
        if include:
            data = data[include]
        exclude = cfg.get('exclude', kwargs.get('exclude', []))
        if exclude:
            data = data.drop(exclude, axis=1)
        # transform rows
        dropna = cfg.get('dropna', kwargs.get('dropna', True))
        if dropna:
            if isinstance(dropna, list):
                subset = dropna
            else:
                subset = None
            data.dropna(subset=subset, inplace=True)
        dedup = kwargs.get('deduplicate', cfg.get('deduplicate', True))
        if dedup:
            if isinstance(dedup, list):
                subset = dedup
            else:
                subset = None
            data.drop_duplicates(subset=subset, inplace=True)
        return data

    def _predict(self, data, score_col=False):
        data = self._transform(data, deduplicate=False)
        self.model = cache.open(self.model_path, joblib.load)
        if score_col and score_col in data:
            target = data[score_col]
            data = data.drop([score_col], axis=1)
            return self.model.score(data, target)
        return self.model.predict(data)

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
            if self.request.headers.get('Content-Type', '') == 'application/json':
                try:
                    data = pd.read_json(self.request.body.decode('utf8'))
                except ValueError:
                    data = DATA_CACHE.get(slugify(self.name), {}).get('data', [])
                    _cache = False
            else:
                data = pd.DataFrame.from_dict(parse_qs(self.request.body.decode('utf8')))
        if _cache:
            orgdf = DATA_CACHE.get(slugify(self.name), {}).get('data', [])
            if len(orgdf):
                data = pd.concat((orgdf, data), axis=0)
            DATA_CACHE[slugify(self.name)]['data'] = data
        if len(data) == 0:
            data = DATA_CACHE.get(slugify(self.name), {}).get('data', [])
        return data

    def _parse_trainopts(self):
        opts = {}
        for opt, default in TRAINING_DEFAULTS.items():
            val = self.args.get(f'{opt}', self.get_opt(f'{opt}', default))
            self.set_opt(opt, val)
            opts[opt] = val
        return opts

    def _coerce_model_params(self, mclass=None, params=None):
        # If you need params for self.model, use mclass, don't rely on self.model attribute
        # if self.model:
        #     model_params = self.model.get_params()
        # else:
        spec = signature(mclass)
        m_args = spec.parameters.keys()
        if 'self' in m_args:
            m_args.remove('self')
        m_defaults = {k: v.default for k, v in spec.parameters.items()}
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

    def _check_model_path(self, error='raise'):
        if not op.exists(self.model_path):
            msg = f'No model found at {self.model_path}'
            if error == 'raise':
                raise HTTPError(NOT_FOUND, log_message=msg)
            else:
                import warnings
                warnings.warn(msg)
        if self.model is None:
            self.model = cache.open(self.model_path, joblib.load)

    @coroutine
    def get(self, *path_args, **path_kwargs):
        if '_opts' in self.args:
            self.write(json.dumps(self.get_opt(), indent=4))
            self.finish()
        if '_download' in self.args:
            self.set_header('Content-Type', 'application/octet-strem')
            self.set_header('Content-Disposition',
                            f'attachment; filename={op.basename(self.model_path)}')
            self.write(open(self.model_path, 'rb').read())
        elif '_model' in self.args:
            if isinstance(self.model, Pipeline):
                for k, v in self.model.named_steps.items():
                    if k != 'transform':
                        break
                params = v.get_params()
            elif isinstance(self.model, BaseEstimator):
                params = self.model.get_params()
            elif self.model is None:
                params = self.get_opt()
            self.write(json.dumps(params, indent=4))
        elif '_cache' in self.args:
            if '_opts' in self.args:
                self.write(json.dumps(self.cache['opts']))
            data = DATA_CACHE[slugify(self.name)].get('data', [])
            if len(data):
                self.write(data.to_json(orient='records'))
            else:
                self.write(json.dumps([]))
        else:
            self.set_header('Content-Type', 'application/json')
            action = self.args.pop('_action', [''])[0]
            try:
                data = pd.DataFrame.from_dict(
                    {k: v for k, v in self.args.items() if not k.startswith('_')})
                if len(data) > 0 and not action:
                    action = 'predict'
            except Exception as err:
                app_log.debug(err.msg)
                data = DATA_CACHE[slugify(self.name)]['data']
            if len(data) == 0:
                data = DATA_CACHE[slugify(self.name)]['data']
            target_col = DATA_CACHE[slugify(self.name)]['target_col']
            if target_col in data:
                target = data.pop(target_col)
            else:
                target = None
            prediction = yield gramex.service.threadpool.submit(self._predict, data)
            if action == 'predict':
                self.write(_serialize_prediction(prediction))
            elif action == 'score':
                score = accuracy_score(target.astype(prediction.dtype),
                                       prediction)
                self.write(json.dumps({'score': score}, indent=4))
            else:
                if isinstance(self.template, str) and op.isfile(self.template):
                    self.render(
                        self.template, handler=self,
                        data=DATA_CACHE[slugify(self.name)].get('data'))
                elif self.template:
                    self.set_header('Content-Type', 'text/html')
                    self.write(estimator_html_repr(self.model))
                else:
                    self.set_header('Content-Type', 'application/json')
                    self.write(json.dumps([]))
        super(MLHandler, self).get(*path_args, **path_kwargs)

    @coroutine
    def post(self, *path_args, **path_kwargs):
        action = self.args.get('_action', ['predict'])[0]
        if action in ('score', 'predict'):
            self._check_model_path()
        if action == 'retrain':
            # Don't parse data from request, just train on the cached data
            data = DATA_CACHE[slugify(self.name)].get('data', [])
        else:
            data = self._parse_data(False)
        if (action == 'score') & (len(data) == 0):
            data = DATA_CACHE[slugify(self.name)].get('data', [])
        if action == 'predict':
            prediction = yield gramex.service.threadpool.submit(self._predict, data)
            self.write(_serialize_prediction(prediction))
        elif action == 'score':
            target_col = self.get_opt('target_col')
            score = yield gramex.service.threadpool.submit(self._predict, data, target_col)
            self.write(json.dumps({'score': score}, indent=4))
        elif action in ('train', 'retrain'):
            target_col = self.args.get('_target_col', [False])[0]
            if not target_col:
                older_target_col = self.get_opt('target_col', False)
                if not older_target_col:
                    raise ValueError('target_col not specified')
                else:
                    target_col = older_target_col
            else:
                self.set_opt('target_col', target_col)

            opts = self._parse_trainopts()
            # filter columns
            data = self._filtercols(data, **opts)

            # filter rows
            data = self._filterrows(data, **opts)

            # assemble the pipeline
            if opts.get('pipeline', True):
                # self.model = self._get_pipeline(data, target_col=target_col, **opts)
                self.model = self._get_pipeline(data, **opts)

            # train the model
            target = data[target_col]
            train = data[[c for c in data if c != target_col]]
            yield gramex.service.threadpool.submit(_fit, self.model, train, target)
            joblib.dump(self.model, self.model_path)
            app_log.info(f'{self.name}: Model saved at {self.model_path}')
            self.write(json.dumps({'score': self.model.score(train, target)}))
        elif action == 'append':
            try:
                self.cache_data(data)
            except Exception as err:
                raise HTTPError(BAD_REQUEST, reason=f'{err}')
        else:
            raise ValueError(f'Action {action} not supported.')
        super(MLHandler, self).post(*path_args, **path_kwargs)

    @property
    def cache(self):
        return DATA_CACHE[slugify(self.name)]

    @coroutine
    def put(self, *path_args, **path_kwargs):
        if '_model' in self.args:
            self.args.pop('_model')
            mclass = self.args.pop('class', [False])[0]
            if not mclass:
                mclass = self.get_opt('class')
            self.set_opt('class', mclass)
            # mclass = search_modelclass(mclass)
            # params = {k: v[0] for k, v in self.args.items() if k not in TRAINING_DEFAULTS}
            # params = self._coerce_model_params(mclass, params)
            # self.set_opt('params', params)
            # self.model = mclass(**params)
            # joblib.dump(self.model, self.model_path)
            # self.write(json.dumps(self.model.get_params(), indent=4))
            for arg, value in self.args.items():
                if arg not in ['include', 'exclude', 'cats', 'nums']:
                    value = value[0]
                self.set_opt(arg, value)
            # Since model params are chaning, remove the model on disk
            self.model = None
            if op.exists(self.model_path):
                os.remove(self.model_path)
        else:
            self._check_model_path()

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        self._check_model_path()
        if '_model' in self.args:
            os.remove(self.model_path)
        if '_cache' in self.args:
            del DATA_CACHE[slugify(self.name)]['data']
            DATA_CACHE[slugify(self.name)]['data'] = []


# class _MLHandler(FormHandler):
#     @classmethod
#     def setup(cls, path='', model_class=None, model_params=None, **kwargs):
#         # process data
#         data = kwargs.pop('data')
#         if isinstance(data, str):
#             filter_kwargs = {}
#             url = data
#         else:
#             url = data.pop('url')
#             filter_kwargs = data
#         DATA_CACHE[cls.name]['data'] = gdata.filter(url, **filter_kwargs)
#         super(MLHandler, cls).setup(**kwargs)
#         if not model_params:
#             model_params = {}
#         if path:
#             cls.model_path = path
#         else:
#             mname = slugify(cls.name) + '.pkl'
#             mpath = op.join(variables['GRAMEXDATA'], 'apps', 'mlhandler')
#             _mkdir(mpath)
#             cls.model_path = op.join(mpath, mname)
#         if op.isfile(path):
#             cls.model = cache.open(path, joblib.load)
#             if model_class:
#                 mclass = search_modelclass(model_class)
#                 if not isinstance(cls.model, mclass):
#                     import textwrap
#                     msg = f'''
#                     The model present at {cls.model_path} is not a {model_class}.
#                     Overwriting it.'''
#                     warnings.warn(textwrap.dedent(msg))
#                     cls.model = mclass(**model_params)
#         elif model_class:
#             mclass = search_modelclass(model_class)
#             cls.model = mclass(**model_params)
#         else:
#             cls.model = None
#         if cls.model:
#             joblib.dump(cls.model, cls.model_path)
#
#     # def _fit(self, data):
#     #     data = self._transform(data)
#     #     target = self.kwargs.get('_target_col', self.get_arg('_target_col'))
#     #     target = data.pop(target)
#     #     DATA_CACHE[self.name]['input'] = data.columns.tolist()
#     #     DATA_CACHE[self.name]['target'] = target.name
#     #     DATA_CACHE[self.name]['train_shape'] = data.shape
#     #     self.pipeline = self._assemble_pipeline(data)
#     #     self.pipeline.fit(data, target)
#     #     joblib.dump(self.pipeline, self.model_path)
#     #     if not self.get_arg('_score', False):
#     #         try:
#     #             score = self.pipeline.score(data, target)
#     #         except AttributeError:
#     #             score = f"A model of type {type(self.model)} does not have a score method."
#     #         SCORES[self.model_path].append(score)
#     #         return SCORES[self.model_path][-1]
#
#     def _predict(self, data):
#         data = self._transform(data)
#         self.model = cache.open(self.model_path, joblib.load)
#         return self.model.predict(data)
#
#     def _score(self, df, prediction, metric='accuracy_score'):
#         y_true = df[self.get_arg('_target_col')].values
#         return getattr(metrics, metric)(y_true, prediction)
#
#     def _coerce_model_params(self, mclass=None, params=None):
#         if self.model:
#             model_params = self.model.get_params()
#         else:
#             spec = getargspec(mclass)
#             m_args = spec.args
#             m_args.remove('self')
#             m_defaults = spec.defaults
#             model_params = {k: v for k, v in zip(m_args, m_defaults)}
#         if not params:
#             new_params = {k: v[0] for k, v in self.args.items() if k in model_params}
#         else:
#             new_params = params
#         param_types = {}
#         for k, v in model_params.items():
#             if v is None:
#                 param_types[k] = str
#             else:
#                 param_types[k] = type(v)
#         return {k: param_types[k](v) for k, v in new_params.items()}
#
#     def _filter_model_params(self, mclass):
#         spec = [c for c in getargspec(mclass).args if c != 'self']
#         return {k: v[0] for k, v in self.args.items() if k in spec}
#
#     def _assemble_pipeline(self, data):
#         if json.loads(self.get_arg('_pipeline', 'false')):
#             nums = set(self.args.get('_nums', []))
#             cats = set(self.args.get('_cats', []))
#             both = nums.intersection(cats)
#             if len(both) > 0:
#                 raise HTTPError(
#                     BAD_REQUEST,
#                     reason=f"Columns {both} cannot be both numerical and categorical.")
#             to_guess = set(data.columns.tolist()) - nums.union(cats)
#             categoricals = [c for c in to_guess if is_categorical(data[c])]
#             for c in categoricals:
#                 to_guess.remove(c)
#             numericals = [c for c in to_guess if pd.api.types.is_numeric_dtype(data[c])]
#             categoricals += list(cats)
#             numericals += list(nums)
#             ct = ColumnTransformer([('ohe', OneHotEncoder(sparse=False), categoricals),
#                                     ('scaler', StandardScaler(), numericals)])
#             return Pipeline([('transform', ct), (self.model.__class__.__name__, self.model)])
#         return self.model
#
#     def _deduplicate(self, df):
#         dedup = json.loads(self.get_arg('_deduplicate', 'true'))
#         if dedup:
#             if isinstance(dedup, list):
#                 subset = dedup
#             else:
#                 subset = None
#             return df.drop_duplicates(subset=subset)
#         return df
#
#     def _dropna(self, df):
#         dropna = json.loads(self.get_arg('_dropna', 'true'))
#         if dropna:
#             if isinstance(dropna, list):
#                 subset = dropna
#             else:
#                 subset = None
#             return df.dropna(subset=subset)
#         return df
#
#     def _filtercols(self, df):
#         target_col = self.kwargs.get('_target_col', self.get_arg('_target_col', False))
#         if target_col:
#             target = df.pop(target_col)
#         include = self.args.get('_include', [])
#         exclude = self.args.get('_exclude', [])
#         if len(include) > 0:
#             df = df[include]
#         if len(exclude) > 0:
#             df.drop(exclude, axis=1, inplace=True)
#         if target_col:
#             df[target_col] = target
#         return df
#
#     def _transform(self, df=None):
#         if df is None:
#             df = DATA_CACHE[self.name]['data'].copy()
#         df = self._deduplicate(df)
#         df = self._dropna(df)
#         df = self._filtercols(df)
#         return df
#
#     @property
#     def _data_cachedir(self):
#         cache_dir = op.join(gettempdir(), self.session['id'])
#         _mkdir(cache_dir)
#         return cache_dir
#
#     @coroutine
#     def get(self, *path_args, **path_kwargs):
#         if self.args.get('_cache', False):
#             out = {k: v for k, v in DATA_CACHE[self.name].items() if k != 'data'}
#             out.update({'data': DATA_CACHE[self.name]['data'].to_dict(orient='records')})
#             self.write(json.dumps(out, indent=4))
#         elif self.args.get('_model', False):
#             out = {'params': self.model.get_params()}
#             out.update({k: v for k, v in DATA_CACHE[self.name].items() if k != 'data'})
#             if len(SCORES[self.model_path]) > 0:
#                 out['score'] = SCORES[self.model_path][-1]
#             out['model'] = self.model.__class__.__name__
#             self.write(json.dumps(out, indent=4))
#         elif self.args.get('_download', False):
#             self.set_header('Content-Type', 'application/octet-strem')
#             self.set_header('Content-Disposition',
#                             f'attachment; filename={op.basename(self.model_path)}')
#             return open(self.model_path, 'rb').read()
#         else:
#             try:
#                 data = pd.DataFrame(self.args)
#             except Exception as err:
#                 app_log.debug(err.msg)
#             prediction = yield gramex.service.threadpool.submit(self._predict, data)
#             self.write(_serialize_prediction(prediction))
#         super(MLHandler, self).get(*path_args, **path_kwargs)
#
#     @coroutine
#     def post(self, *path_args, **path_kwargs):
#         if self.get_arg('_retrain', False):
#             data = self._parse_data()
#             score = yield gramex.service.threadpool.submit(self._fit, data)
#             self.write(json.dumps(dict(score=score), indent=4))
#         else:
#             data = self._parse_data(False)
#             prediction = yield gramex.service.threadpool.submit(self._predict, data)
#             if self.get_arg('_score', False):
#                 self.write({'score': self._score(data, prediction)})
#             else:
#                 self.write(_serialize_prediction(prediction))
#         super(MLHandler, self).get(*path_args, **path_kwargs)
#
#     @coroutine
#     def put(self, *path_args, **path_kwargs):
#         # TODO: If we change the model class, GET ?_model does not return the new one
#         mclass = self.args.pop('class')[0]
#         _retrain = self.args.pop('_retrain', False)
#         if not op.isfile(self.model_path):
#             mclass = search_modelclass(mclass)
#             mparams = self._filter_model_params(mclass)
#             mparams = self._coerce_model_params(mclass, mparams)
#             self.model = mclass(**mparams)
#         else:
#             self.model = cache.open(self.model_path, joblib.load)
#             mclass = search_modelclass(mclass)
#             model_kwargs = self._coerce_model_params()
#             if not isinstance(self.model, mclass):
#                 self.model = mclass(**model_kwargs)
#             else:
#                 [setattr(self.model, k, v) for k, v in model_kwargs.items()]
#         joblib.dump(self.model, self.model_path)
#         out = {'model': self.model.__class__.__name__,
#                'params': self.model.get_params()}
#         if _retrain:
#             data = self._parse_data()
#             score = yield gramex.service.threadpool.submit(self._fit, data)
#             out.update({'score': score})
#         self.write(json.dumps(out, indent=4))
#
#     @coroutine
#     def delete(self, *path_args, **path_kwargs):
#         if self.args.get('_cache', False):
#             if self.name in DATA_CACHE:
#                 del DATA_CACHE[self.name]
#         else:
#             if not op.isfile(self.model_path):
#                 raise HTTPError(NOT_FOUND, reason=f'Model {self.model_path} does not exist.')
#             os.remove(self.model_path)
