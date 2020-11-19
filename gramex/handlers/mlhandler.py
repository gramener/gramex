from collections import defaultdict
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
from tornado.gen import coroutine
from tornado.web import HTTPError

op = os.path
DATA_CACHE = {}
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
    return json.dumps(obj)


class MLHandler(FormHandler):
    @classmethod
    def setup(cls, path='', model_class=None, model_params=None, **kwargs):
        super(MLHandler, cls).setup(**kwargs)
        if not model_params:
            model_params = {}
        if path:
            cls.model_path = path
        else:
            cls.model_path = op.join(variables['YAMLPATH'], op.basename(cls.name) + '.pkl')
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
        else:
            mclass = search_modelclass(model_class)
            cls.model = mclass(**model_params)
        joblib.dump(cls.model, cls.model_path)

    def _fit(self, data):
        data = self._filtercols(data)
        target = self.kwargs.get('target_col', self.get_arg('target_col'))
        target = data.pop(target)
        self.model.fit(data, target)
        joblib.dump(self.model, self.model_path)
        if not self.get_arg('_score', False):
            try:
                score = self.model.score(data, target)
            except AttributeError:
                score = f"A model of type {type(self.model)} does not have a score method."
            SCORES[self.model_path].append(score)
            return SCORES[self.model_path][-1]

    def _predict(self, data):
        data = self._filtercols(data)
        return self.model.predict(data)

    def _coerce_model_params(self):
        model_params = self.model.get_params()
        new_params = {k: v[0] for k, v in self.args.items() if k in model_params}
        param_types = {}
        for k, v in model_params.items():
            if v is None:
                param_types[k] = str
            else:
                param_types[k] = type(v)
        return {k: param_types[k](v) for k, v in new_params.items()}

    def _filtercols(self, data):
        include = self.args.get('_include', [])
        exclude = self.args.get('_exclude', [])
        if len(include) > 0:
            data = data[include]
        if len(exclude) > 0:
            data.drop(exclude, axis=1, inplace=True)
        return data

    @property
    def _data_cachedir(self):
        cache_dir = op.join(gettempdir(), self.session['id'])
        _mkdir(cache_dir)
        return cache_dir

    @coroutine
    def get(self, *path_args, **path_kwargs):
        if '_model' in self.args:
            out = {'params': self.model.get_params()}
            if len(SCORES[self.model_path]) > 0:
                out['score'] = SCORES[self.model_path][-1]
            self.write(out)
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
                    dfs.append(gramex.cache.open(outpath))
            data = pd.concat(dfs, axis=0)
        # Otherwise look in request.body
        else:
            data = pd.read_json(self.request.body.decode('utf8'))
        if _cache:
            orgdf = DATA_CACHE.get(self.name, [])
            if len(orgdf):
                data = pd.concat((orgdf, data), axis=0)
                DATA_CACHE[self.name] = data
        return data

    @coroutine
    def post(self, *path_args, **path_kwargs):
        if self.get_arg('_retrain', False):
            data = self._parse_data()
            score = yield gramex.service.threadpool.submit(self._fit, data)
            self.write(dict(score=score))
        else:
            data = self._parse_data(False)
            prediction = yield gramex.service.threadpool.submit(self._predict, data)
            self.write(_serialize_prediction(prediction))
        super(MLHandler, self).get(*path_args, **path_kwargs)

    @coroutine
    def put(self, *path_args, **path_kwargs):
        # TODO: If we change the model class, GET ?_model does not return the new one
        mclass = self.args.pop('class')[0]
        if not op.isfile(self.model_path):
            self.model = search_modelclass(mclass)(
                **{k: v[0] for k, v in self.args.items()})
        else:
            self.model = joblib.load(self.model_path)
            mclass = search_modelclass(mclass)
            model_kwargs = self._coerce_model_params()
            if not isinstance(self.model, mclass):
                self.model = mclass(**model_kwargs)
            else:
                [setattr(self.model, k, v) for k, v in model_kwargs.items()]
        joblib.dump(self.model, self.model_path)
        if self.get_arg('_retrain', False):
            data = self._parse_data()
            score = yield gramex.service.threadpool.submit(self._fit, data)
            self.write({'score': score})
        else:
            self.write({'params': self.model.get_params()})

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        if self.get_arg('_cache', False):
            if self.name in DATA_CACHE:
                del DATA_CACHE[self.name]
        else:
            if not op.isfile(self.model_path):
                raise HTTPError(NOT_FOUND, reason=f'Model {self.model_path} does not exist.')
            os.remove(self.model_path)
