from inspect import signature
from io import BytesIO
import json
import os
import re

import gramex
from gramex.config import app_log, CustomJSONEncoder, locate
from gramex import data as gdata
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND, BAD_REQUEST
from gramex.install import _mkdir, safe_rmtree
from gramex import cache
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder
from slugify import slugify
from tornado.gen import coroutine
from tornado.web import HTTPError
try:
    from transformers import pipeline
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from transformers import Trainer, TrainingArguments
    from gramex.dl_utils import SentimentDataset
except ImportError:
    TRANSFORMERS_INSTALLED = False


op = os.path
MLCLASS_MODULES = [
    'sklearn.linear_model',
    'sklearn.tree',
    'sklearn.ensemble',
    'sklearn.svm',
    'sklearn.neighbors',
    'sklearn.neural_network',
    'sklearn.naive_bayes',
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
}
ACTIONS = ['predict', 'score', 'append', 'train', 'retrain']
TRANSFORMERS_DEFAULTS = dict(
    num_train_epochs=1,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    weight_decay=0.01,
    warmup_steps=100,
)
SENTIMENT_LENC = LabelEncoder().fit(['NEGATIVE', 'POSITIVE'])
DEFAULT_TEMPLATE = op.join(op.dirname(__file__), '..', 'apps', 'mlhandler', 'template.html')
search_modelclass = lambda x: locate(x, MLCLASS_MODULES)  # NOQA: E731


def _fit(model, x, y, path=None, name=None):
    app_log.info('Starting training...')
    getattr(model, 'partial_fit', model.fit)(x, y)
    app_log.info('Done training...')
    joblib.dump(model, path)
    app_log.info(f'{name}: Model saved at {path}.')
    return model


def _train_transformer(model, data, model_path, **kwargs):
    enc = model.tokenizer(data['text'].tolist(), truncation=True, padding=True)
    labels = SENTIMENT_LENC.transform(data['label'])
    train_dataset = SentimentDataset(enc, labels)
    model_output_dir = op.join(op.dirname(model_path), 'results')
    model_log_dir = op.join(op.dirname(model_path), 'logs')
    trargs = TrainingArguments(
        output_dir=model_output_dir, logging_dir=model_log_dir, **kwargs)
    Trainer(model=model.model, args=trargs, train_dataset=train_dataset).train()
    model.save_pretrained(model_path)
    move_to_cpu(model)
    pred = model(data['text'].tolist())
    res = {
        'roc_auc': roc_auc_score(
            labels, SENTIMENT_LENC.transform([c['label'] for c in pred]))
    }
    return res


def _score_transformer(model, data):
    pred = model(data['text'].tolist())
    score = roc_auc_score(
        *map(SENTIMENT_LENC.transform, (data['label'], [c['label'] for c in pred])))
    return {'roc_auc': score}


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
        return s.nunique() / s.shape[0] <= num_treshold
    return True


def move_to_cpu(model):
    getattr(model, 'model', model).to('cpu')


class BaseMLHandler(FormHandler):

    @classmethod
    def setup(cls, data=None, model=None, config_dir='', **kwargs):
        cls.slug = slugify(cls.name)
        # Create the config store directory
        # use config_dir or DEFAULT_VALUE
        if not config_dir:
            config_dir = op.join(gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler',
                                 cls.slug)
        _mkdir(config_dir)
        cls.config_dir = config_dir
        cls.config_store = cache.JSONStore(op.join(cls.config_dir, 'config.json'), flush=None)
        cls.data_store = op.join(cls.config_dir, 'data.h5')

        cls.template = kwargs.pop('template', DEFAULT_TEMPLATE)
        super(BaseMLHandler, cls).setup(**kwargs)

    @classmethod
    def store_data(cls, df, append=False):
        df.to_hdf(cls.data_store, format="table", key="data", append=append)
        try:
            rdf = gramex.cache.open(cls.data_store, key="data")
        except KeyError:
            rdf = df
        return rdf

    @classmethod
    def load_data(cls):
        try:
            df = gramex.cache.open(cls.data_store, key="data")
        except (KeyError, FileNotFoundError):
            df = pd.DataFrame()
        return df

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

        if _cache:
            self.store_data(data, append)
        return data

    def _coerce_transformers_opts(self):
        kwargs = {k: self.get_arg(k, TRANSFORMERS_DEFAULTS.get(k)) for k in TRANSFORMERS_DEFAULTS}
        kwargs = {k: type(TRANSFORMERS_DEFAULTS.get(k))(v) for k, v in kwargs.items()}
        return kwargs

    @classmethod
    def load_transformer(cls, task, _model={}):
        default_model_path = op.join(
            gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler',
            slugify(cls.name))
        path = _model.get('path', default_model_path)
        cls.model_path = path
        # try loading from model_path
        kwargs = {}
        if task == "ner":
            kwargs['grouped_entities'] = True
        try:
            kwargs['model'] = AutoModelForSequenceClassification.from_pretrained(cls.model_path)
            kwargs['tokenizer'] = AutoTokenizer.from_pretrained(cls.model_path)
        except Exception as err:
            app_log.warning(f'Could not load model from {cls.model_path}.')
            app_log.warning(f'{err}')
        model = pipeline(task, **kwargs)
        cls.model = model


class MLHandler(BaseMLHandler):

    @classmethod
    def setup(cls, data=None, model={}, backend='sklearn', config_dir='', **kwargs):
        task = kwargs.pop('task', False)
        if backend != 'sklearn':
            if not TRANSFORMERS_INSTALLED:
                raise ImportError('pip install transformers')
            super(MLHandler, cls).setup(**kwargs)
            cls.load_transformer(task, model)
            cls.get = NLPHandler.get
            cls.post = NLPHandler.post
            cls.delete = NLPHandler.delete
        else:
            super(MLHandler, cls).setup(data, model, config_dir, **kwargs)
            try:
                data = gdata.filter(**data)
                cls.store_data(data)
            except TypeError:
                data = None

            default_model_path = op.join(
                gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler',
                slugify(cls.name) + '.pkl')
            cls.model_path = model.pop('path', default_model_path)
            _mkdir(op.dirname(cls.model_path))

            # store the model kwargs from gramex.yaml into the store
            for key in TRANSFORMS:
                cls.set_opt(key, model.get(key, cls.get_opt(key)))
            cls.set_opt('class', model.get('class'))
            cls.set_opt('params', model.get('params', {}))
            target_col = cls.get_opt('target_col')

            if op.exists(cls.model_path):  # If the pkl exists, load it
                cls.model = joblib.load(cls.model_path)
            else:
                mclass = cls.get_opt('class', model.get('class', False))
                params = cls.get_opt('params', {})
                if mclass:
                    cls.model = search_modelclass(mclass)(**params)
                    cls.set_opt('class', mclass)
                else:
                    cls.model = None

                if cls.model is not None:
                    if not target_col:
                        app_log.warning('Target column not defined. Nothing to do.')
                    elif data is not None:
                        data = cls._filtercols(data)
                        data = cls._filterrows(data)

                        cls.model = cls._assemble_pipeline(data, mclass=mclass, params=params)

                        # train the model
                        target = data[target_col]
                        train = data[[c for c in data if c != target_col]]
                        gramex.service.threadpool.submit(
                            _fit, cls.model, train, target, cls.model_path, cls.name)
            cls.config_store.flush()

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
        nums = set(cls.get_opt('nums', []))
        cats = set(cls.get_opt('cats', []))
        both = nums.intersection(cats)
        if len(both) > 0:
            raise HTTPError(BAD_REQUEST,
                            reason=f"Columns {both} cannot be both numerical and categorical.")
        to_guess = set(data.columns.tolist()) - nums.union(cats) - {cls.get_opt('target_col')}
        categoricals = [c for c in to_guess if is_categorical(data[c])]
        for c in categoricals:
            to_guess.remove(c)
        numericals = [c for c in to_guess if pd.api.types.is_numeric_dtype(data[c])]
        categoricals += list(cats)
        numericals += list(nums)
        assert len(set(categoricals) & set(numericals)) == 0

        ct = ColumnTransformer(
            [('ohe', OneHotEncoder(sparse=False), categoricals),
             ('scaler', StandardScaler(), numericals)]
        )
        model_kwargs = cls.config_store.load('model', {})
        mclass = model_kwargs.get('class', False)
        if mclass:
            model = search_modelclass(mclass)(**model_kwargs.get('params', {}))
            cls.set_opt('params', model.get_params())
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
        if data is None:
            data = self._parse_data(False)
        data = self._transform(data, drop_duplicates=False)
        self.model = cache.open(self.model_path, joblib.load)
        try:
            target = data.pop(score_col)
            return self.model.score(data, target)
        except KeyError:
            # Set data in the same order as the transformer requests
            data = data[self.model.named_steps['transform']._feature_names_in]
            data[self.get_opt('target_col', '_prediction')] = self.model.predict(data)
            return data

    def _check_model_path(self):
        try:
            self.model = cache.open(self.model_path, joblib.load)
        except FileNotFoundError:
            raise HTTPError(NOT_FOUND, f'No model found at {self.model_path}')

    @coroutine
    def prepare(self):
        flattened = {}
        for k, v in self.args.items():
            if not isinstance(TRANSFORMS.get(k), list) and isinstance(v, list) and len(v) == 1:
                v = v[0]
            flattened[k] = v
        self.args = flattened

    @coroutine
    def get(self, *path_args, **path_kwargs):
        if '_params' in self.args:
            params = {
                'opts': self.config_store.load('transform'),
                'params': self.config_store.load('model')
            }
            self.write(json.dumps(params, indent=2))
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
                    self.set_header('Content-Type', 'application/json')
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
        target = data[target_col]
        train = data[[c for c in data if c != target_col]]
        self.model = self._assemble_pipeline(data, force=True)
        _fit(self.model, train, target, self.model_path)
        return {'score': self.model.score(train, target)}

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
            raise ValueError(f'Action {action} not supported.')
        res = yield gramex.service.threadpool.submit(getattr(self, f"_{action}"))
        self.write(json.dumps(res, indent=2, cls=CustomJSONEncoder))
        super(MLHandler, self).post(*path_args, **path_kwargs)

    def get_cached_arg(self, argname):
        val = self.get_arg(argname, self.get_opt(argname))
        self.set_opt(argname, val)
        return val

    @coroutine
    def put(self, *path_args, **path_kwargs):
        mclass = self.args.pop('class', self.get_opt('class'))
        self.set_opt('class', mclass)
        params = self.get_opt('params', {})
        if mclass:
            # parse the params as the signature dictates
            for param in signature(search_modelclass(mclass)).parameters:
                if param in self.args:
                    value = self.args.pop(param)
                    params[param] = value
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
        self.store_data(pd.DataFrame())

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


class NLPHandler(BaseMLHandler):

    @classmethod
    def setup(cls, task, model={}, config_dir='', **kwargs):
        cls.task = task
        if not TRANSFORMERS_INSTALLED:
            raise ImportError('pip install transformers')
        super(NLPHandler, cls).setup(**kwargs)
        cls.load_transformer(task, model)

    @coroutine
    def get(self, *path_args, **path_kwargs):
        text = self.get_arguments('text')
        result = yield gramex.service.threadpool.submit(self.model, text)
        self.write(json.dumps(result, indent=2))

    @coroutine
    def post(self, *path_args, **path_kwargs):
        # Data should always be present as [{'text': ..., 'label': ...}, {'text': ...}] arrays
        data = self._parse_data(_cache=False)
        action = self.args.get('_action', ['predict'])[0]
        move_to_cpu(self.model)
        kwargs = {}
        if action == 'train':
            if self.task == "ner":
                raise HTTPError(BAD_REQUEST,
                                reason="Action not yet supported for task {self.task}")
            kwargs = self._coerce_transformers_opts()
            kwargs['model_path'] = self.model_path
            args = _train_transformer, self.model, data
        elif action == 'score':
            if self.task == "ner":
                raise HTTPError(BAD_REQUEST,
                                reason="Action not yet supported for task {self.task}")
            args = _score_transformer, self.model, data
        elif self.task == "sentiment-analysis":
            args = self.model, data['text'].tolist()
            res = yield gramex.service.threadpool.submit(*args, **kwargs)
        elif self.task == "ner":
            res = yield gramex.service.threadpool.submit(lambda x: [self.model(k) for k in x],
                                                         data['text'].tolist())
        self.write(json.dumps(res, indent=2, cls=CustomJSONEncoder))

    @coroutine
    def delete(self, *path_args, **path_kwargs):
        safe_rmtree(self.model_path, gramexdata=False)
