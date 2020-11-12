from collections import defaultdict
import json
import os

from gramex.config import app_log
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND
from gramex import cache, service
import joblib
import numpy as np
import pandas as pd
import sklearn
import sklearn.neighbors
import sklearn.naive_bayes
import sklearn.ensemble
import sklearn.neural_network
from sklearn.base import BaseEstimator
from tornado.gen import coroutine
from tornado.web import HTTPError

op = os.path
SCORES = defaultdict(list)
SKLEARN_CLASSES = dict(
    LogisticRegression=sklearn.linear_model,
    RidgeClassifier=sklearn.linear_model,
    SGDClassifier=sklearn.linear_model,
    Preceptron=sklearn.linear_model,
    PassiveAggressiveClassifier=sklearn.linear_model,
    SVC=sklearn.svm,
    KNeighborsClassifier=sklearn.neighbors,
    GaussianNB=sklearn.naive_bayes,
    MultinomialNB=sklearn.naive_bayes,
    RandomForestClassifier=sklearn.ensemble,
    DecisionTreeClassifier=sklearn.tree,
    MLPClassifier=sklearn.neural_network
)


def _serialize_prediction(obj):
    # Serialize a list or an array or a tensor
    if isinstance(obj, np.ndarray):
        obj = obj.tolist()
    return json.dumps(obj)


class MLHandler(FormHandler):
    @classmethod
    def setup(cls, model=None, model_kwargs=None, model_access=None, **kwargs):
        super(MLHandler, cls).setup(**kwargs)
        cls.model = model
        if model_kwargs is None:
            model_kwargs = {}
        cls.model_kwargs = model_kwargs
        cls.model_access = model_access
        if model:
            if op.isfile(model):
                cls.model = cache.open(model, joblib.load)
                cls.model_path = model
            else:
                class_module = SKLEARN_CLASSES.get(model, False)
                if not class_module:
                    raise ValueError('Algorithm not supported.')
                mclass = getattr(class_module, model)
                cls.model = mclass(**model_kwargs)
                cls.model_path = model if model.endswith('.pkl') else model + '.pkl'
                joblib.dump(cls.model, cls.model_path)

        if isinstance(cls.model, BaseEstimator):
            cls.engine = 'sklearn'
        else:
            cls.engine = ''

    def _fit(self, data):
        target = self.kwargs.get('target_col', self.get_arg('target_col'))
        target = data.pop(target)
        self.model.fit(data, target)
        joblib.dump(self.model, self.model_path)
        if not self.get_arg('_score', False):
            SCORES[self.model_path].append(self.model.score(data, target))
            return SCORES[self.model_path][-1]

    def _predict(self, data):
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

    @coroutine
    def get(self, *path_args, **path_kwargs):
        if self.engine == 'sklearn':
            if '_model' in self.args:
                self.write({
                    'params': self.model.get_params(),
                    'score': SCORES[self.model_path][-1]
                })
            else:
                try:
                    data = pd.DataFrame(self.args)
                except Exception as err:
                    app_log.debug(err.msg)
                prediction = yield service.threadpool.submit(self._predict, data)
                self.write(_serialize_prediction(prediction))
        super(MLHandler, self).get(*path_args, **path_kwargs)

    @coroutine
    def post(self, *path_args, **path_kwargs):
        if self.engine == 'sklearn':
            data = pd.read_json(self.request.body.decode('utf8'))
            if self.get_arg('_retrain', False):
                score = yield service.threadpool.submit(self._fit, data)
                self.write(dict(score=score))
            else:
                prediction = yield service.threadpool.submit(self._predict, data)
                self.write(_serialize_prediction(prediction))
        super(MLHandler, self).get(*path_args, **path_kwargs)

    @coroutine
    def put(self, *path_args, **path_kwargs):
        self.model_path = path_args[0] + '.pkl'
        mclass = self.args.pop('class')[0]
        if not op.isfile(self.model_path):
            self.model = getattr(SKLEARN_CLASSES.get(mclass), mclass)(
                **{k: v[0] for k, v in self.args.items()})
        else:
            self.model = joblib.load(self.model_path)
            mclass = getattr(SKLEARN_CLASSES.get(mclass), mclass)
            model_kwargs = self._coerce_model_params()
            if not isinstance(self.model, mclass):
                self.model = mclass(**model_kwargs)
            else:
                [setattr(self.model, k, v) for k, v in model_kwargs.items()]
        joblib.dump(self.model, self.model_path)
        if self.get_arg('_retrain', False):
            data = pd.read_json(self.request.body.decode('utf8'))
            score = yield service.threadpool.submit(self._fit, data)
            self.write({'score': score})
        else:
            self.write({'params': self.model.get_params()})

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        model_path = path_args[0] + '.pkl'
        if not op.isfile(model_path):
            raise HTTPError(NOT_FOUND, reason=f'Model {model_path} does not exist.')
        os.remove(model_path)
