from collections import defaultdict
import json
import os

import gramex
from gramex.config import app_log, variables
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND
from gramex import cache
import joblib
import numpy as np
import pandas as pd
import sklearn
import sklearn.neighbors
import sklearn.naive_bayes
import sklearn.ensemble
import sklearn.neural_network
from tornado.gen import coroutine
from tornado.web import HTTPError

op = os.path
SCORES = defaultdict(list)
# TODO: Can we just search across all possible namespaces for the class, and avoid this totally?
# TODO: Include statsmodels as well. Do not include as an explicit dependency. Try to import
# TODO: Fallback to libraries for search: sklearn - statsmodels - keras - ...
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
    MLPClassifier=sklearn.neural_network,
    LinearRegression=sklearn.linear_model,
    DecisionTreeRegressor=sklearn.tree,
)


def _serialize_prediction(obj):
    # Serialize a list or an array or a tensor
    if isinstance(obj, np.ndarray):
        obj = obj.tolist()
    return json.dumps(obj)


class MLHandler(FormHandler):
    @classmethod
    def setup(cls, path='', model_class=None, model_params=None, **kwargs):
        super(MLHandler, cls).setup(**kwargs)
        if path:
            cls.model_path = path
        else:
            cls.model_path = op.join(variables['YAMLPATH'], op.basename(cls.name) + '.pkl')
        if op.isfile(path):
            cls.model = cache.open(path, joblib.load)
            # TODO: If it's not the same as gramex.yaml model, then re-create with a warning
        else:
            class_module = SKLEARN_CLASSES.get(model_class, False)
            if not class_module:
                raise ValueError('Algorithm not supported.')
            if not model_params:
                model_params = {}
            mclass = getattr(class_module, model_class)
            cls.model = mclass(**model_params)
            joblib.dump(cls.model, cls.model_path)

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

    @coroutine
    def post(self, *path_args, **path_kwargs):
        # TODO: [IMP]: Instead, concat all self.request.files read via gramex.cache.open with the
        #   relevant filename.ext.
        # TODO: This should append to a data store
        # TODO: Support defining input columns, not just target columns
        data = pd.read_json(self.request.body.decode('utf8'))
        if self.get_arg('_retrain', False):
            score = yield gramex.service.threadpool.submit(self._fit, data)
            self.write(dict(score=score))
        else:
            prediction = yield gramex.service.threadpool.submit(self._predict, data)
            self.write(_serialize_prediction(prediction))
        super(MLHandler, self).get(*path_args, **path_kwargs)

    @coroutine
    def put(self, *path_args, **path_kwargs):
        # TODO: If we change the model class, GET ?_model does not return the new one
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
            score = yield gramex.service.threadpool.submit(self._fit, data)
            self.write({'score': score})
        else:
            self.write({'params': self.model.get_params()})

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        if not op.isfile(self.model_path):
            raise HTTPError(NOT_FOUND, reason=f'Model {self.model_path} does not exist.')
        os.remove(self.model_path)
