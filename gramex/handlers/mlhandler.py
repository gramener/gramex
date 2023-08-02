from io import BytesIO
import json
import os
import re

import gramex
from gramex import ml_api as ml
from gramex.transforms import build_transform
from gramex.config import app_log, CustomJSONEncoder, locate
from gramex import data as gdata
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND, BAD_REQUEST
from gramex.install import safe_rmtree
from gramex import cache

import numpy as np
import pandas as pd
import joblib
from sklearn.base import TransformerMixin
from sklearn.pipeline import Pipeline
from slugify import slugify
from tornado.gen import coroutine
from tornado.web import HTTPError
from sklearn.metrics import get_scorer

# TODO: Redesign the template for usecases
# MLHandler2 - API is more streamlined.

op = os.path

ACTIONS = ['predict', 'score', 'append', 'train', 'retrain']
DEFAULT_TEMPLATE = op.join(op.dirname(__file__), '..', 'apps', 'mlhandler', 'template.html')


def get_model(mclass: str, model_params: dict, **kwargs) -> ml.AbstractModel:
    if not mclass:
        return
    if mclass.endswith('.pkl'):
        model = cache.open(mclass, joblib.load)
        if isinstance(model, Pipeline):
            _, wrapper = ml.search_modelclass(model[-1].__class__.__name__)
        else:
            _, wrapper = ml.search_modelclass(model.__class__.__name__)
    else:
        mclass, wrapper = ml.search_modelclass(mclass)
        try:
            model = mclass(**model_params)
        except TypeError:
            model = mclass
    return locate(wrapper)(model, params=model_params, **kwargs)


class MLHandler(FormHandler):
    @classmethod
    def setup(cls, data=None, model={}, config_dir='', template=DEFAULT_TEMPLATE, **kwargs):
        if not config_dir:
            config_dir = op.join(
                gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler', slugify(cls.name)
            )
        cls.store = ml.ModelStore(config_dir)
        cls.template = template
        super(MLHandler, cls).setup(**kwargs)
        index_col = None
        try:
            if 'transform' in data:
                cls.store.dump('built_transform', data['transform'])
                data['transform'] = build_transform(
                    {'function': data['transform']},
                    vars={'data': None, 'handler': None},
                    filename='MLHandler:data',
                    iter=False,
                )
                cls._built_transform = staticmethod(data['transform'])
            else:
                cls._built_transform = staticmethod(lambda x: x)
            index_col = data.get('index_col')
            cls.store.dump('index_col', index_col)
            data = gdata.filter(**data)
            cls.store.store_data(data)
        except TypeError:
            app_log.warning('MLHandler could not find training data.')
            data = None
            cls._built_transform = staticmethod(lambda x: x)

        # store the model kwargs from gramex.yaml into the store
        for key in ml.TRANSFORMS:
            cls.store.dump(key, model.get(key, cls.store.load(key)))
        # Remove target_col if it appears anywhere in cats or nums
        target_col = cls.store.load('target_col')
        nums = list(set(cls.store.load('nums')) - {target_col})
        cats = list(set(cls.store.load('cats')) - {target_col})
        cls.store.dump('cats', cats)
        cls.store.dump('nums', nums)

        mclass = model.get('class', cls.store.load('class', ''))
        model_params = model.get('params', {})
        cls.store.dump('class', mclass)
        cls.store.dump('params', model_params)
        if op.exists(cls.store.model_path):  # If the pkl exists, load it
            if op.isdir(cls.store.model_path):
                mclass, wrapper = ml.search_modelclass(mclass)
                cls.model = locate(wrapper).from_disk(cls.store.model_path, mclass)
            else:
                cls.model = get_model(cls.store.model_path, {})
        elif data is not None:
            data = cls._filtercols(data)
            data = cls._filterrows(data)
            cls.model = get_model(
                mclass, model_params, data=data, cats=cats, nums=nums, target_col=target_col
            )
            # train the model
            if issubclass(cls.model.__class__, TransformerMixin):
                target = None
                train = data
            else:
                target = data[target_col]
                train = data.drop([target_col], axis=1)
            gramex.service.threadpool.submit(
                cls.model.fit,
                train,
                target,
                model_path=cls.store.model_path,
                name=cls.name,
                **cls.store.model_kwargs(),
            )

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
        return pd.read_json(self.request.body.decode('utf-8'))

    def _parse_data(self, _cache=True, append=False):
        header = self.request.headers.get('Content-Type', '').split(';')[0]
        header = slugify(header).replace('-', '_')
        try:
            data = getattr(self, f'_parse_{header}')()
        except AttributeError:
            app_log.warning(f"Content-Type {header} not supported, reading cached data.")
            data = self.store.load_data()
        except ValueError:
            app_log.warning('Could not read data from request, reading cached data.')
            data = self.store.load_data()
        data = self._built_transform(data)

        if _cache:
            self.store.store_data(data, append)
        return data

    @classmethod
    def _filtercols(cls, data, **kwargs):
        include = kwargs.get('include', cls.store.load('include', []))
        if include:
            include += [cls.store.load('target_col')]
            data = data[include]
        else:
            exclude = kwargs.get('exclude', cls.store.load('exclude', []))
            to_exclude = [c for c in exclude if c in data]
            if to_exclude:
                data = data.drop(to_exclude, axis=1)
        return data

    @classmethod
    def _filterrows(cls, data, **kwargs):
        for method in ('dropna', 'drop_duplicates'):
            action = kwargs.get(method, cls.store.load(method, True))
            if action:
                subset = action if isinstance(action, list) else None
                try:
                    data = getattr(data, method)(subset=subset)
                except TypeError as exc:
                    # The label column for an NER dataset is a nested list.
                    # Can't do drop_duplicates on that.
                    app_log.warning(exc)
        return data

    def _transform(self, data, **kwargs):
        orgdata = self.store.load_data()
        for col in np.intersect1d(data.columns, orgdata.columns):
            data[col] = data[col].astype(orgdata[col].dtype)
        data = self._filtercols(data, **kwargs)
        data = self._filterrows(data, **kwargs)
        return data

    def _predict(self, data=None, score_col=''):
        self._check_model_path()
        metric = self.get_argument('_metric', False)
        if metric:
            scorer = get_scorer(metric)
        if data is None:
            data = self._parse_data(False)
        data = self._transform(data, drop_duplicates=False)
        try:
            target = data.pop(score_col)
            if metric:
                return scorer(self.model, data, target)
            return self.model.score(data, target)
        except KeyError:
            # Set data in the same order as the transformer requests
            try:
                tcol = self.store.load('target_col', '_prediction')
                data = self.model.predict(data, target_col=tcol)
            except Exception as exc:
                app_log.exception(exc)
            return data

    def _check_model_path(self):
        try:
            klass, wrapper = ml.search_modelclass(self.store.load('class'))
            self.model = locate(wrapper).from_disk(self.store.model_path, klass=klass)
        except FileNotFoundError:
            raise HTTPError(NOT_FOUND, f'No model found at {self.store.model_path}')

    @coroutine
    def prepare(self):
        super(MLHandler, self).prepare()
        flattened = {}
        for k, v in self.args.items():
            if not isinstance(ml.TRANSFORMS.get(k), list) and isinstance(v, list) and len(v) == 1:
                v = v[0]
            flattened[k] = v
        self.args = flattened

    @coroutine
    def get(self, *path_args, **path_kwargs):
        self.set_header('Content-Type', 'application/json')
        if '_params' in self.args:
            params = {'opts': self.store.load('transform'), 'params': self.store.load('model')}
            try:
                attrs = get_model(self.store.model_path, {}).get_attributes()
            except (AttributeError, ImportError, FileNotFoundError):
                attrs = {}
            params['attrs'] = attrs
            self.write(json.dumps(params, indent=2, cls=CustomJSONEncoder))
        elif '_cache' in self.args:
            self.write(self.store.load_data().to_json(orient='records'))
        else:
            self._check_model_path()
            if '_download' in self.args:
                self.set_header('Content-Type', 'application/octet-strem')
                self.set_header(
                    'Content-Disposition',
                    f'attachment; filename={op.basename(self.store.model_path)}',
                )
                with open(self.store.model_path, 'rb') as fout:
                    self.write(fout.read())
            elif '_model' in self.args:
                self.write(json.dumps(self.model.get_params(), indent=2))
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
                    data = data.drop([self.store.load('target_col')], axis=1, errors='ignore')
                    prediction = yield gramex.service.threadpool.submit(self._predict, data)
                    self.write(json.dumps(prediction, indent=2, cls=CustomJSONEncoder))
                else:
                    self.set_header('Content-Type', 'text/html')
                    self.render(self.template, handler=self, data=self.store.load_data())
        super(MLHandler, self).get(*path_args, **path_kwargs)

    def _append(self):
        self._parse_data(_cache=True, append=True)

    def _train(self, data=None):
        target_col = self.get_argument('target_col', self.store.load('target_col'))
        index_col = self.get_argument('index_col', self.store.load('index_col'))
        self.store.dump('target_col', target_col)
        data = self._parse_data(False) if data is None else data
        data = self._filtercols(data)
        data = self._filterrows(data)
        self.model = get_model(
            self.store.load('class'),
            self.store.load('params'),
            data=data,
            target_col=target_col,
            nums=self.store.load('nums'),
            cats=self.store.load('cats'),
        )
        if not isinstance(self.model, ml.SklearnTransformer):
            target = data[target_col]
            train = data[[c for c in data if c not in (target_col, index_col)]]
            self.model.fit(train, target, self.store.model_path)
            result = {'score': self.model.score(train, target)}
        else:
            self.model.fit(data, None, self.store.model_path)
            result = self.model.get_attributes()
        return result

    def _retrain(self):
        return self._train(self.store.load_data())

    def _score(self):
        self._check_model_path()
        data = self._parse_data(False)
        target_col = self.get_argument('target_col', self.store.load('target_col'))
        self.store.dump('target_col', target_col)
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
        mclass = self.args.pop('class', False)
        if mclass:
            self.store.dump('class', mclass)
        else:
            mclass = self.store.load('class')
        for opt in ml.TRANSFORMS.keys() & self.args.keys():
            val = self.args.pop(opt)
            self.store.dump(opt, val)
        # The rest is params
        params = self.store.load('params')
        for key, val in ml.coerce_model_params(mclass, self.args).items():
            params[key] = val
        self.store.dump('params', params)

    def _delete_model(self):
        safe_rmtree(self.store.model_path, gramexdata=False)
        self.store.purge()

    def _delete_cache(self):
        self.store.store_data(pd.DataFrame(), mode="w")

    def _delete_opts(self):
        for opt in set(self.get_arguments('_opts')) & ml.TRANSFORMS.keys():
            self.store.dump(opt, ml.TRANSFORMS[opt])

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        for item in self.get_arguments('delete'):
            try:
                getattr(self, f'_delete_{item}')()
            except AttributeError:
                raise HTTPError(BAD_REQUEST, f'Cannot delete {item}.')


class MLPredictor(FormHandler):
    @classmethod
    def setup(cls, config_dir, data, target_col=None, columns=None, **kwargs):
        cls.config_dir = config_dir
        cls.cols = columns
        cls.target_col = target_col
        kwargs.update(data)
        super(MLPredictor, cls).setup(**kwargs)

    def _filtercols(self, data):
        """Filter columns from the input dataframe, as follows:

        1. If columns are specified, use only those columns and ignore everything else.
        2. Otherwise fall back on config_dir/config.json

        Note: From sklearn 1.x onwards, ColumnTransformer (which is the default
        preprocessor used in MLHandler) stores the names of columns.
        When Gramex supports it, we will not need to store column information in config.json
        """
        if self.cols is not None:
            return data[self.cols]
        store = ml.ModelStore(self.config_dir)
        include = store.load('include')
        if len(include):
            return data[include]
        exclude = store.load('exclude')
        target = store.load('target_col', False)
        if target and target not in exclude:
            exclude.append(target)
        return data.drop(exclude, axis=1)

    def modify_all(self, data=None, key=None, handler=None):
        model = cache.open(op.join(self.config_dir, "model.pkl"), joblib.load)
        df = self._filtercols(data['data'])
        store = ml.ModelStore(self.config_dir)
        target = self.target_col or store.load('target_col', None) or 'prediction'
        df[target] = model.predict(df)
        return {'data': df}
