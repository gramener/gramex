from inspect import signature, _empty
from io import BytesIO
import json
import os
import re

import gramex
from gramex.transforms import build_transform
from gramex.config import app_log, CustomJSONEncoder, locate
from gramex import data as gdata
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND, BAD_REQUEST
from gramex.install import _mkdir, safe_rmtree
from gramex import cache

import joblib
import pandas as pd
from sklearn.base import TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from slugify import slugify
from tornado.gen import coroutine
from tornado.web import HTTPError
from sklearn.metrics import get_scorer

op = os.path
MLCLASS_MODULES = [
    'sklearn.linear_model',
    'sklearn.tree',
    'sklearn.ensemble',
    'sklearn.svm',
    'sklearn.neighbors',
    'sklearn.neural_network',
    'sklearn.naive_bayes',
    'sklearn.decomposition',
    'gramex.ml',
    'gramex.sm_api'
]
TRANSFORMS = {
    'include': [],
    'exclude': [],
    'dropna': True,
    'drop_duplicates': True,
    'pipeline': True,
    'nums': [],
    'cats': [],
    'target_col': None,
    'index_col': None
}
ACTIONS = ['predict', 'score', 'append', 'train', 'retrain']
DEFAULT_TEMPLATE = op.join(op.dirname(__file__), '..', 'apps', 'mlhandler', 'template.html')
is_statsmodel = lambda x: x.__module__ == 'gramex.sm_api'  # NOQA: E731


def search_modelclass(mclass):
    _class = locate(mclass, MLCLASS_MODULES)
    if _class is None:
        raise ImportError(f'{mclass} not found.')
    return _class


def _fit(model, x, y=None, path=None, name=None, **kwargs):
    app_log.info('Starting training...')
    try:
        getattr(model, 'partial_fit', model.fit)(x, y, **kwargs)
        app_log.info('Done training...')
        joblib.dump(model, path)
        app_log.info(f'{name}: Model saved at {path}.')
    except Exception as exc:
        app_log.exception(exc)
    return model


class MLHandler(FormHandler):

    @classmethod
    def setup(cls, data=None, model={}, config_dir='', **kwargs):
        cls.slug = slugify(cls.name)
        # Create the config store directory
        if not config_dir:
            config_dir = op.join(gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler',
                                 cls.slug)
        _mkdir(config_dir)
        cls.config_dir = config_dir
        cls.config_store = cache.JSONStore(op.join(cls.config_dir, 'config.json'), flush=None)
        cls.data_store = op.join(cls.config_dir, 'data.h5')

        cls.template = kwargs.pop('template', DEFAULT_TEMPLATE)
        super(MLHandler, cls).setup(**kwargs)
        index_col = None
        try:
            if 'transform' in data:
                data['transform'] = build_transform(
                    {'function': data['transform']},
                    vars={'data': None, 'handler': None},
                    filename='MLHandler:data', iter=False)
                cls._built_transform = staticmethod(data['transform'])
            else:
                cls._built_transform = staticmethod(lambda x: x)
            index_col = data.get('index_col')
            cls.set_opt('index_col', index_col)
            data = gdata.filter(**data)
            cls.store_data(data)
        except TypeError:
            app_log.warning('MLHandler could not find training data.')
            data = None
            cls._built_transform = staticmethod(lambda x: x)

        default_model_path = op.join(cls.config_dir, slugify(cls.name) + '.pkl')
        cls.model_path = model.pop('path', default_model_path)

        # store the model kwargs from gramex.yaml into the store
        for key in TRANSFORMS:
            cls.set_opt(key, model.get(key, cls.get_opt(key)))
        # Remove target_col if it appears anywhere in cats or nums
        target_col = cls.get_opt('target_col')
        cls.set_opt('cats', list(set(cls.get_opt('cats')) - {target_col}))
        cls.set_opt('nums', list(set(cls.get_opt('nums')) - {target_col}))

        cls.set_opt('class', model.get('class'))
        cls.set_opt('params', model.get('params', {}))
        if op.exists(cls.model_path):  # If the pkl exists, load it
            cls.model = joblib.load(cls.model_path)
        elif data is not None:
            mclass = cls.get_opt('class', model.get('class', False))
            params = cls.get_opt('params', {})
            data = cls._filtercols(data)
            data = cls._filterrows(data)
            cls.model = cls._assemble_pipeline(data, mclass=mclass, params=params)

            # train the model
            if issubclass(search_modelclass(mclass), TransformerMixin):
                target = None
                train = data
            else:
                target = data[target_col]
                train = data.drop([target_col], axis=1)
            _fit_kwargs = {'index_col': index_col} if index_col else {}
            gramex.service.threadpool.submit(
                _fit, cls.model, train, target, cls.model_path, cls.name,
                **_fit_kwargs
            )

    @classmethod
    def load_data(cls, default=pd.DataFrame()):
        try:
            df = gramex.cache.open(cls.data_store, key="data")
        except (KeyError, FileNotFoundError):
            df = default
        return df

    @classmethod
    def store_data(cls, df, append=False, **kwargs):
        df.to_hdf(cls.data_store, format="table", key="data", append=append, **kwargs)
        return cls.load_data(df)

    @classmethod
    def get_opt(cls, key, default=None):
        return cls.config_store.load('transform', {}).get(
            key, TRANSFORMS.get(
                key, cls.config_store.load('model', {}).get(key, default)
            )
        )

    @classmethod
    def set_opt(cls, key, value):
        if key in TRANSFORMS:
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

    def _parse_multipart_form_data(self):
        dfs = []
        for _, files in self.request.files.items():
            for f in files:
                buff = BytesIO(f['body'])
                try:
                    ext = re.sub(r'^.', '', op.splitext(f['filename'])[-1])
                    xdf = cache.open_callback['jsondata' if ext == 'json' else ext](buff)
                    dfs.append(xdf)
                except KeyError:
                    app_log.warning(f"File extension {ext} not supported.")
                    continue
        return pd.concat(dfs, axis=0)

    def _parse_application_json(self):
        return pd.read_json(self.request.body.decode('utf8'))

    def _parse_data(self, _cache=True, append=False):
        header = self.request.headers.get('Content-Type', '').split(';')[0]
        header = slugify(header).replace('-', '_')
        try:
            data = getattr(self, f'_parse_{header}')()
        except AttributeError:
            app_log.warning(f"Content-Type {header} not supported, reading cached data.")
            data = self.load_data()
        except ValueError:
            app_log.warning('Could not read data from request, reading cached data.')
            data = self.load_data()
        data = self._built_transform(data)

        if _cache:
            self.store_data(data, append)
        return data

    @classmethod
    def _filtercols(cls, data, **kwargs):
        include = kwargs.get('include', cls.get_opt('include', []))
        if include:
            include += [cls.get_opt('target_col')]
            data = data[include]
        else:
            exclude = kwargs.get('exclude', cls.get_opt('exclude', []))
            to_exclude = [c for c in exclude if c in data]
            if to_exclude:
                data = data.drop(to_exclude, axis=1)
        return data

    @classmethod
    def _filterrows(cls, data, **kwargs):
        for method in 'dropna drop_duplicates'.split():
            action = kwargs.get(method, cls.get_opt(method, True))
            if action:
                subset = action if isinstance(action, list) else None
                data = getattr(data, method)(subset=subset)
        return data

    @classmethod
    def _assemble_pipeline(cls, data, force=False, mclass='', params=None):
        # If the model exists, return it
        if op.exists(cls.model_path) and not force:
            return joblib.load(cls.model_path)

        # If preprocessing is not enabled, return the root model
        if not cls.get_opt('pipeline', True):
            return search_modelclass(mclass)(**params)

        # Else assemble the preprocessing pipeline
        nums = set(cls.get_opt('nums', [])) - {cls.get_opt('target_col')}
        cats = set(cls.get_opt('cats', [])) - {cls.get_opt('target_col')}
        both = nums.intersection(cats)
        if len(both) > 0:
            raise HTTPError(BAD_REQUEST,
                            reason=f"Columns {both} cannot be both numerical and categorical.")
        to_guess = set(data.columns.tolist()) - nums.union(cats) - {cls.get_opt('target_col')}
        numericals = list(nums)
        categoricals = list(cats)
        for c in to_guess:
            if pd.api.types.is_numeric_dtype(data[c]):
                numericals.append(c)
            else:
                categoricals.append(c)

        model_kwargs = cls.config_store.load('model', {})
        mclass = model_kwargs.get('class', False)
        if mclass:
            model = search_modelclass(mclass)(**model_kwargs.get('params', {}))
            cls.set_opt('params', model.get_params())
            if is_statsmodel(model):
                cls.model = model
            else:
                ct = ColumnTransformer(
                    [('ohe', OneHotEncoder(sparse=False), categoricals),
                     ('scaler', StandardScaler(), numericals)]
                )
                return Pipeline([('transform', ct), (model.__class__.__name__, model)])
        return cls.model

    def _transform(self, data, **kwargs):
        orgdata = self.load_data()
        for col in data:
            data[col] = data[col].astype(orgdata[col].dtype)
        data = self._filtercols(data, **kwargs)
        data = self._filterrows(data, **kwargs)
        return data

    def _predict(self, data=None, score_col=''):
        metric = self.get_argument('_metric', False)
        if metric:
            scorer = get_scorer(metric)
        if data is None:
            data = self._parse_data(False)
        self.model = cache.open(self.model_path, joblib.load)
        if is_statsmodel(self.model):
            p = self.model.predict(data, target_col=self.get_opt('target_col'), **self.args)
            if score_col:
                return self.model.score(data, p, score_col)
            return p

        data = self._transform(data, drop_duplicates=False)
        try:
            target = data.pop(score_col)
            if metric:
                return scorer(self.model, data, target)
            return self.model.score(data, target)
        except KeyError:
            # Set data in the same order as the transformer requests
            try:
                data = data[self.model.named_steps['transform']._feature_names_in]
                if isinstance(self.model[-1], TransformerMixin):
                    data = self.model.transform(data)
                else:
                    data[self.get_opt('target_col', '_prediction')] = self.model.predict(data)
            except Exception as exc:
                app_log.exception(exc)
            return data

    def _check_model_path(self):
        try:
            self.model = cache.open(self.model_path, joblib.load)
        except FileNotFoundError:
            raise HTTPError(NOT_FOUND, f'No model found at {self.model_path}')

    @coroutine
    def prepare(self):
        super(MLHandler, self).prepare()
        flattened = {}
        for k, v in self.args.items():
            if not isinstance(TRANSFORMS.get(k), list) and isinstance(v, list) and len(v) == 1:
                v = v[0]
            flattened[k] = v
        self.args = flattened

    @coroutine
    def get(self, *path_args, **path_kwargs):
        self.set_header('Content-Type', 'application/json')
        if '_params' in self.args:
            params = {
                'opts': self.config_store.load('transform'),
                'params': self.config_store.load('model')
            }
            try:
                model = cache.open(self.model_path, joblib.load)
                if is_statsmodel(model):
                    attrs = model.res.summary().as_html()
                else:
                    attrs = {
                        k: v for k, v in vars(model[-1]).items() if re.search(r'[^_]+_$', k)
                    }
            except FileNotFoundError:
                attrs = {}
            params['attrs'] = attrs
            self.write(json.dumps(params, indent=2, cls=CustomJSONEncoder))
        elif '_cache' in self.args:
            self.write(self.load_data().to_json(orient='records'))
        else:
            self._check_model_path()
            if '_download' in self.args:
                self.set_header('Content-Type', 'application/octet-strem')
                self.set_header('Content-Disposition',
                                f'attachment; filename={op.basename(self.model_path)}')
                with open(self.model_path, 'rb') as fout:
                    self.write(fout.read())
            elif '_model' in self.args:
                self.write(json.dumps(self.get_opt('params'), indent=2))
            else:
                try:
                    data_args = {k: v for k, v in self.args.items() if not k.startswith('_')}
                    data_args = {
                        k: [v] if not isinstance(v, list) else v for k, v in data_args.items()
                    }
                    data = pd.DataFrame.from_dict(data_args)
                except Exception as err:
                    app_log.debug(err.msg)
                    data = []
                if len(data) > 0:
                    data = data.drop([self.get_opt('target_col')], axis=1, errors='ignore')
                    prediction = yield gramex.service.threadpool.submit(
                        self._predict, data)
                    self.write(json.dumps(prediction, indent=2, cls=CustomJSONEncoder))
                else:
                    self.set_header('Content-Type', 'text/html')
                    self.render(self.template, handler=self, data=self.load_data())
        super(MLHandler, self).get(*path_args, **path_kwargs)

    def _append(self):
        self._parse_data(_cache=True, append=True)

    def _train(self, data=None):
        target_col = self.get_argument('target_col', self.get_opt('target_col'))
        self.set_opt('target_col', target_col)
        data = self._parse_data(False) if data is None else data
        data = self._filtercols(data)
        data = self._filterrows(data)
        self.model = self._assemble_pipeline(data, force=True)
        if is_statsmodel(self.model):
            result = _fit(
                self.model, None, data, self.model_path, target_col=target_col,
                index_col=self.get_argument('index_col')
            )
            self.set_header('Content-Type', 'text/html')
        elif not isinstance(self.model[-1], TransformerMixin):
            target = data[target_col]
            train = data[[c for c in data if c != target_col]]
            _fit(self.model, train, target, self.model_path)
            result = {'score': self.model.score(train, target)}
        else:
            _fit(self.model, data, path=self.model_path)
            # Note: Fitted sklearn estimators store their parameters
            # in attributes whose names end in an underscore. E.g. in the case of PCA,
            # attributes are named `explained_variance_`. The `_train` action returns them.
            result = {k: v for k, v in vars(self.model[-1]).items() if re.search(r'[^_]+_$', k)}
        return result

    def _retrain(self):
        return self._train(self.load_data())

    def _score(self):
        self._check_model_path()
        data = self._parse_data(False)
        target_col = self.get_argument('target_col', self.get_opt('target_col'))
        self.set_opt('target_col', target_col)
        return {'score': self._predict(data, target_col)}

    @coroutine
    def post(self, *path_args, **path_kwargs):
        action = self.args.pop('_action', 'predict')
        if action not in ACTIONS:
            raise HTTPError(BAD_REQUEST, f'Action {action} not supported.')
        res = yield gramex.service.threadpool.submit(getattr(self, f"_{action}"))
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(res, indent=2, cls=CustomJSONEncoder))
        super(MLHandler, self).post(*path_args, **path_kwargs)

    @coroutine
    def put(self, *path_args, **path_kwargs):
        mclass = self.args.pop('class', self.get_opt('class'))
        self.set_opt('class', mclass)
        params = self.get_opt('params', {})
        if mclass:
            # parse the params as the signature dictates
            sig_params = signature(search_modelclass(mclass)).parameters
            for param in sig_params & self.args.keys():
                val = self.args.pop(param)
                _sig_p = sig_params[param]
                annotation = _sig_p.annotation
                val = annotation(val) if annotation is not _empty else type(_sig_p.default)(val)
                params[param] = val

        # Since model params are changing, remove the model on disk
        self.model = None
        safe_rmtree(self.model_path, gramexdata=False)
        self.set_opt('params', params)
        for opt in TRANSFORMS.keys() & self.args.keys():
            val = self.args.pop(opt)
            self.set_opt(opt, val)
        self.config_store.flush()

    def _delete_model(self):
        safe_rmtree(self.model_path, gramexdata=False)
        self.config_store.purge()

    def _delete_cache(self):
        self.store_data(pd.DataFrame(), mode="w")

    def _delete_opts(self):
        for opt in set(self.get_arguments('_opts')) & TRANSFORMS.keys():
            self.set_opt(opt, TRANSFORMS[opt])

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        for item in self.get_arguments('delete'):
            try:
                getattr(self, f'_delete_{item}')()
            except AttributeError:
                raise HTTPError(BAD_REQUEST, f'Cannot delete {item}.')
