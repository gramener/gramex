from collections import defaultdict
from inspect import signature
import json
import os
from urllib.parse import parse_qs

import gramex
from gramex.config import app_log, CustomJSONEncoder
from gramex import data as gdata
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND, BAD_REQUEST
from gramex.install import _mkdir
from gramex import cache
import joblib
import pandas as pd
import pydoc
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score
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
TRAINING_DEFAULTS = {
    'include': [],
    'exclude': [],
    'dropna': True,
    'deduplicate': True,
    'pipeline': True,
    'nums': [],
    'cats': [],
    'target_col': None,
}
DEFAULT_TEMPLATE = op.join(op.dirname(__file__), '..', 'apps', 'mlhandler', 'template.html')
_prediction_col = '_prediction'


def df2url(df):
    s = ['&'.join([f'{k}={v}' for k, v in r.items()]) for r in df.to_dict(orient='records')]
    return '&'.join(s)


def _fit(model, x, y, path=None, name=None):
    app_log.info('Starting training...')
    getattr(model, 'partial_fit', model.fit)(x, y)
    app_log.info('Done training...')
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


def is_categorical(s, num_treshold=0.1):
    """Check if a series contains a categorical variable.

    Parameters
    ----------
    s : pd.Series

    Returns
    -------
    bool:
        Whether the series is categorical.
        uniques / count <= num_treshold / log(count)
    """
    if pd.api.types.is_numeric_dtype(s):
        if s.nunique() / s.shape[0] <= num_treshold:
            return True
        return False
    return True


class MLHandler(FormHandler):

    @classmethod
    def store_data(cls, df, append=False):
        if op.exists(cls.data_store) and append:
            df = pd.concat((pd.read_hdf(cls.data_store, 'data'), df), axis=0, ignore_index=True)
        df.to_hdf(cls.data_store, 'data')
        return df

    @classmethod
    def load_data(cls):
        if op.exists(cls.data_store):
            return gramex.cache.open(cls.data_store)
        return pd.DataFrame()

    @classmethod
    def get_opt(cls, key, default=None):
        if key in TRAINING_DEFAULTS:
            return cls.config_store.load('transform', {}).get(key, TRAINING_DEFAULTS[key])
        if key in ('class', 'params'):
            return cls.config_store.load('model', {}).get(key, default)

    @classmethod
    def set_opt(cls, key, value):
        if key in TRAINING_DEFAULTS:
            transform = cls.config_store.load('transform', {})
            transform[key] = value
            cls.config_store.dump('transform', transform)
            cls.config_store.update['transform'] = transform
        elif key in ('class', 'params'):
            model = cls.config_store.load('model', {})
            model[key] = value
            if key == 'class':
                app_log.warning('Model changed, removing old parameters.')
                model['params'] = {}
            cls.config_store.dump('model', model)
            cls.config_store.update['model'] = model
        cls.config_store.changed = True
        cls.config_store.flush()

    @classmethod
    def setup(cls, data=None, model=None, config_dir='', **kwargs):
        cls.slug = slugify(cls.name)
        if not op.isdir(config_dir):
            config_dir = op.join(gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler',
                                 cls.slug)
            _mkdir(config_dir)
        cls.config_dir = config_dir
        cls.uploads_dir = op.join(config_dir, 'uploads')
        _mkdir(cls.uploads_dir)
        cls.config_store = cache.JSONStore(op.join(cls.config_dir, 'config.json'), flush=None)
        cls.data_store = op.join(cls.config_dir, 'data.h5')
        cls.template = kwargs.pop('template', True)
        super(MLHandler, cls).setup(**kwargs)
        if isinstance(data, str):
            data = cache.open(data)
        elif isinstance(data, dict):
            data = gdata.filter(**data)
        else:
            data = None
        if data is not None:
            cls.store_data(data)

        # parse model kwargs
        if model is None:
            model = {}

        default_model_path = op.join(
            gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler',
            slugify(cls.name) + '.pkl')
        model_path = model.pop('path', default_model_path)

        # store the model kwargs from gramex.yaml into the store
        for key in TRAINING_DEFAULTS:
            kwarg = model.get(key, False)
            if not cls.get_opt(key, False) and kwarg:
                cls.set_opt(key, kwarg)
        if op.exists(model_path):  # If the pkl exists, load it
            cls.model = joblib.load(model_path)
            cls.model_path = model_path
            target_col = model.get('target_col', False)
            if target_col:
                cls.set_opt('target_col', target_col)
            else:
                target_col = cls.get_opt('target_col')
        else:  # build the model
            mclass = cls.get_opt('class', model.get('class', False))
            params = cls.get_opt('params', {})
            if not params:
                params = model.get('params', {})
            if mclass:
                cls.model = search_modelclass(mclass)(**params)
                cls.set_opt('class', mclass)
            else:
                cls.model = None
            # Params MUST come after class, or they will be ignored.
            cls.set_opt('params', params)

            if model_path:  # if a path is specified, use to to store the model
                cls.model_path = model_path
            else:  # or create our own path
                cls.model_path = default_model_path
                _mkdir(op.dirname(cls.model_path))

            # train the model
            target_col = model.get('target_col', False)
            if target_col:
                cls.set_opt('target_col', target_col)
            else:
                target_col = cls.get_opt('target_col', False)
            if cls.model is not None and not target_col:
                app_log.warning('Target column not defined. Nothing to do.')
            else:
                if cls.model is not None:
                    if data is not None:
                        # filter columns
                        data = cls._filtercols(data)

                        # filter rows
                        data = cls._filterrows(data)

                        # assemble the pipeline
                        if model.get('pipeline', True):
                            cls.model = cls._get_pipeline(data)
                        else:
                            cls.model = search_modelclass(mclass)(**params)

                        # train the model
                        target = data[target_col]
                        train = data[[c for c in data if c != target_col]]
                        if model.get('async', True):
                            gramex.service.threadpool.submit(
                                _fit, cls.model, train, target, cls.model_path, cls.name)
                        else:
                            _fit(cls.model, train, target, cls.model_path, cls.name)
        cls.config_store.flush()

    @classmethod
    def _filtercols(cls, data):
        include = cls.get_opt('include', [])
        if include:
            include += [cls.get_opt('target_col')]
            data = data[include]
        else:
            exclude = cls.get_opt('exclude', [])
            to_exclude = [c for c in exclude if c in data]
            if to_exclude:
                data = data.drop(to_exclude, axis=1)
        return data

    @classmethod
    def _filterrows(cls, data):
        for method in 'dropna drop_duplicates'.split():
            action = cls.get_opt(method, True)
            if action:
                if isinstance(action, list):
                    subset = action
                else:
                    subset = None
                data = getattr(data, method)(subset=subset)
        return data

    @classmethod
    def _get_pipeline(cls, data, force=False):
        # If the model exists, return it
        if op.exists(cls.model_path) and not force:
            return joblib.load(cls.model_path)
        # If there's no data, return None
        if data is None or not len(data):
            return None
        # Else assemble the model
        nums = set(cls.get_opt('nums', []))
        cats = set(cls.get_opt('cats', []))
        both = nums.intersection(cats)
        if len(both) > 0:
            raise HTTPError(
                BAD_REQUEST,
                reason=f"Columns {both} cannot be both numerical and categorical.")
        to_guess = set(data.columns.tolist()) - nums.union(cats)
        target_col = cls.get_opt('target_col', False)
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
        model_kwargs = cls.config_store.load('model', {})
        mclass = model_kwargs.get('class', False)
        if mclass:
            model = search_modelclass(mclass)(**model_kwargs.get('params', {}))
            return Pipeline([('transform', ct), (model.__class__.__name__, model)])
        return cls.model

    def _transform(self, data, **kwargs):
        orgdata = self.load_data()
        for col in data:
            data[col] = data[col].astype(orgdata[col].dtype)
        # transform columns
        include = self.get_opt('include', kwargs.get('include', []))
        if include:
            data = data[include]
        exclude = self.get_opt('exclude', kwargs.get('exclude', []))
        to_exclude = [c for c in exclude if c in data]
        if to_exclude:
            data = data.drop(to_exclude, axis=1)
        # transform rows
        dropna = self.get_opt('dropna', kwargs.get('dropna', True))
        if dropna:
            if isinstance(dropna, list) and len(dropna) > 0:
                subset = dropna
            else:
                subset = None
            data.dropna(subset=subset, inplace=True)
        dedup = self.get_opt('deduplicate', kwargs.get('deduplicate', True))
        if dedup:
            if isinstance(dedup, list):
                subset = dedup
            else:
                subset = None
            data.drop_duplicates(subset=subset, inplace=True)
        return data

    def _predict(self, data, score_col=False, transform=True):
        if transform:
            data = self._transform(data, deduplicate=False)
        self.model = cache.open(self.model_path, joblib.load)
        if score_col and score_col in data:
            target = data[score_col]
            data = data.drop([score_col], axis=1)
            return self.model.score(data, target)
        # Set data in the same order as the transformer requests
        data = data[self.model.named_steps['transform']._feature_names_in]
        data[self.get_opt('target_col', _prediction_col)] = self.model.predict(data)
        return data

    def _parse_data(self, _cache=True):
        # First look in self.request.files
        if len(self.request.files) > 0:
            dfs = []
            for _, files in self.request.files.items():
                for f in files:
                    outpath = op.join(self.uploads_dir, f['filename'])
                    with open(outpath, 'wb') as fout:
                        fout.write(f['body'])
                    if outpath.endswith('.json'):
                        xdf = cache.open(outpath, pd.read_json)
                    else:
                        xdf = cache.open(outpath)
                    dfs.append(xdf)
                    os.remove(outpath)
            data = pd.concat(dfs, axis=0)
        # Otherwise look in request.body
        else:
            if self.request.headers.get('Content-Type', '') == 'application/json':
                try:
                    data = pd.read_json(self.request.body.decode('utf8'))
                except ValueError:
                    data = self.load_data()
                    _cache = False
            else:
                data = pd.DataFrame.from_dict(parse_qs(self.request.body.decode('utf8')))
        if _cache:
            self.store_data(data)
        if len(data) == 0:
            data = self.load_data()
        return data

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
        if '_download' in self.args:
            self.set_header('Content-Type', 'application/octet-strem')
            self.set_header('Content-Disposition',
                            f'attachment; filename={op.basename(self.model_path)}')
            self.write(open(self.model_path, 'rb').read())
        elif '_model' in self.args:
            self._check_model_path()
            if isinstance(self.model, Pipeline):
                for k, v in self.model.named_steps.items():
                    if k != 'transform':
                        break
                params = v.get_params()
            elif isinstance(self.model, BaseEstimator):
                params = self.model.get_params()
            elif self.model is None:
                params = self.get_opt('params')
            self.write(json.dumps(params, indent=4))
        elif '_cache' in self.args:
            if '_opts' in self.args:
                self.write(json.dumps(self.config_store.load('transform')))
                self.finish()
            elif '_params' in self.args:
                self.write(json.dumps(self.config_store.load('model')))
                self.finish()
            else:
                data = self.load_data()
                if len(data):
                    self.write(data.to_json(orient='records'))
                else:
                    self.write(json.dumps([]))
        else:
            self._check_model_path()
            self.set_header('Content-Type', 'application/json')
            action = self.args.pop('_action', [''])[0]
            try:
                data = pd.DataFrame.from_dict(
                    {k: v for k, v in self.args.items() if not k.startswith('_')})
                if len(data) > 0 and not action:
                    action = 'predict'
            except Exception as err:
                app_log.debug(err.msg)
                data = self.load_data()
            if len(data) == 0:
                data = self.load_data()
            target_col = self.get_opt('target_col')
            if target_col in data:
                target = data[target_col]
                to_predict = data.drop([target_col], axis=1)
            else:
                target = None
                to_predict = data
            if action in ('predict', 'score'):
                prediction = yield gramex.service.threadpool.submit(
                    self._predict, to_predict)
                if action == 'predict':
                    self.write(json.dumps(prediction, indent=4, cls=CustomJSONEncoder))
                elif action == 'score':
                    prediction = prediction[target_col if target_col else _prediction_col]
                    score = accuracy_score(target.astype(prediction.dtype),
                                           prediction)
                    self.write(json.dumps({'score': score}, indent=4))
            else:
                if isinstance(self.template, str) and op.isfile(self.template):
                    self.set_header('Content-Type', 'text/html')
                    # return Template(self.template)
                    self.render(
                        self.template, handler=self,
                        data=self.load_data())
                elif self.template:
                    self.set_header('Content-Type', 'text/html')
                    self.render(DEFAULT_TEMPLATE, handler=self, data=self.load_data())
                else:
                    self.set_header('Content-Type', 'application/json')
                    self.write(json.dumps([]))
        super(MLHandler, self).get(*path_args, **path_kwargs)

    @coroutine
    def post(self, *path_args, **path_kwargs):
        action = self.args.get('_action', ['predict'])
        if not set(action).issubset({'predict', 'score', 'append', 'train', 'retrain'}):
            raise ValueError(f'Action {action} not supported.')
        if len(action) == 1:
            action = action[0]

        if action in ('score', 'predict'):
            self._check_model_path()
        if action == 'retrain':
            # Don't parse data from request, just train on the cached data
            data = self.load_data()
        else:
            data = self._parse_data(False)

        if (action == 'score') & (len(data) == 0):
            data = self.load_data()

        if action == 'predict':
            prediction = yield gramex.service.threadpool.submit(
                self._predict, data)
            self.write(json.dumps(prediction, indent=4, cls=CustomJSONEncoder))
        elif action == 'score':
            target_col = self.get_opt('target_col')
            if target_col is None:
                target_col = self.get_arg('target_col')
                self.set_opt('target_col', target_col)
            score = yield gramex.service.threadpool.submit(
                self._predict, data, target_col, transform=False)
            self.write(json.dumps({'score': score}, indent=4))
        elif (action == 'append') or ('append' in action):
            try:
                data = self.store_data(data, append=True)
            except Exception as err:
                raise HTTPError(BAD_REQUEST, reason=f'{err}')
            if isinstance(action, list) and ('append' in action):
                action.remove('append')
                if len(action) == 1:
                    action = action[0]

        if action in ('train', 'retrain'):
            target_col = self.args.get('target_col', [False])[0]
            if not target_col:
                older_target_col = self.get_opt('target_col', False)
                if not older_target_col:
                    raise ValueError('target_col not specified')
                else:
                    target_col = older_target_col
            else:
                self.set_opt('target_col', target_col)

            # filter columns
            data = self._filtercols(data)

            # filter rows
            data = self._filterrows(data)

            # assemble the pipeline
            if self.get_opt('pipeline', True):
                self.model = self._get_pipeline(data, force=True)
            # train the model
            target = data[target_col]
            train = data[[c for c in data if c != target_col]]
            yield gramex.service.threadpool.submit(_fit, self.model, train, target)
            # _fit(self.model, train, target)
            joblib.dump(self.model, self.model_path)
            app_log.info(f'{self.name}: Model saved at {self.model_path}')
            self.write(json.dumps({'score': self.model.score(train, target)}))
        super(MLHandler, self).post(*path_args, **path_kwargs)

    @coroutine
    def put(self, *path_args, **path_kwargs):
        if '_model' in self.args:
            self.args.pop('_model')
            mclass = self.args.pop('class', [False])[0]
            if mclass:
                self.set_opt('class', mclass)
            else:
                mclass = self.get_opt('class')
            params = self.get_opt('params', {})
            if mclass is not None:
                # parse the params as the signature dictates
                for param in signature(search_modelclass(mclass)).parameters:
                    if param in self.args:
                        value = self.args.pop(param)
                        if len(value) == 1:
                            value = value[0]
                        params[param] = value

            # Since model params are changing, remove the model on disk
            self.model = None
            if op.exists(self.model_path):
                os.remove(self.model_path)
            self.set_opt('params', params)

            for opt, default in TRAINING_DEFAULTS.items():
                if opt in self.args:
                    val = self.args.pop(opt)
                    if not isinstance(default, list):
                        if isinstance(val, list) and len(val) == 1:
                            val = val[0]
                    self.set_opt(opt, val)

            self.config_store.flush()
        else:
            self._check_model_path()

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        if '_model' in self.args:
            if '_opts' in self.args:
                for k, default in TRAINING_DEFAULTS.items():
                    if k in self.args:
                        self.set_opt(k, default)
            elif op.exists(self.model_path):
                os.remove(self.model_path)
                self.config_store.purge()
        if '_cache' in self.args:
            self.store_data(pd.DataFrame())
