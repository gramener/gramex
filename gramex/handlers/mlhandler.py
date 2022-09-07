from io import BytesIO
import json
import os
import re

import gramex
from gramex import ml_api as ml
from gramex.config import app_log, CustomJSONEncoder, locate
from gramex.handlers import FormHandler
from gramex.http import NOT_FOUND, BAD_REQUEST
from gramex.install import safe_rmtree
from gramex import cache

import pandas as pd
from slugify import slugify
from tornado.gen import coroutine
from tornado.web import HTTPError

# TODO: Redesign the template for usecases

op = os.path

ACTIONS = ['predict', 'score', 'append', 'train', 'retrain']
DEFAULT_TEMPLATE = op.join(op.dirname(__file__), '..', 'apps', 'mlhandler', 'template.html')


def get_model(
        data_config: dict = None,
        model_config: dict = None,
        store: str = None, **kwargs) -> ml.AbstractModel:
    if data_config is None:
        data_config = {}
    if model_config is None:
        model_config = {}
    params = store.load('params', {})  # To repopulate after recreating the class
    klass = model_config.pop('class', store.load('class'))
    store.dump('class', klass)
    store.dump('params', params)
    try:
        klass, wrapper = ml.search_modelclass(klass)
    except ValueError:
        app_log.warning('No model specification found.')
        return
    model = locate(wrapper)(klass, store, data_config, **model_config)
    return model


class MLHandler(FormHandler):

    @classmethod
    def setup(cls, data={}, model={}, config_dir='', template=DEFAULT_TEMPLATE, **kwargs):
        if not config_dir:
            config_dir = op.join(gramex.config.variables['GRAMEXDATA'], 'apps', 'mlhandler',
                                 slugify(cls.name))
        cls.store = ml.ModelStore(config_dir, model)
        cls.template = template
        super(MLHandler, cls).setup(**kwargs)
        cls.data_config = data
        cls.model_config = model
        cls.model = get_model(data, model, cls.store, **kwargs)

        # Fit the model, if model and data exist
        if cls.model:
            gramex.service.threadpool.submit(
                cls.model._init_fit, name=cls.name,
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
        return pd.read_json(self.request.body.decode('utf8'))

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
        if _cache:
            self.store.store_data(data, append)
        return data

    def _predict(self, data=None):
        self._check_model_path()
        if data is None:
            data = self._parse_data(False)
        try:
            tcol = self.store.load('target_col', '_prediction')
            data = self.model.predict(data, target_col=tcol)
        except Exception as exc:
            app_log.exception(exc)
        return data

    def _check_model_path(self):
        try:
            klass, wrapper = ml.search_modelclass(self.store.load('class'))
            self.model = locate(wrapper).from_disk(self.store, klass=klass)
        except FileNotFoundError:
            raise HTTPError(NOT_FOUND, f'No model found at {self.store.model_path}')
        except ValueError:
            raise HTTPError(NOT_FOUND, 'No model definition found.')

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
            params = {
                'opts': self.store.load('transform'),
                'params': self.store.load('model')
            }
            try:
                self._check_model_path()
                attrs = self.model.get_attributes()
            except (AttributeError, ImportError, FileNotFoundError, HTTPError):
                app_log.warning('No reasonable model found: either saved or defined in the spec.')
                attrs = {}
            params['attrs'] = attrs
            self.write(json.dumps(params, indent=2, cls=CustomJSONEncoder))
        elif '_cache' in self.args:
            self.write(self.store.load_data().to_json(orient='records'))
        else:
            self._check_model_path()
            if '_download' in self.args:
                self.set_header('Content-Type', 'application/octet-strem')
                self.set_header('Content-Disposition',
                                f'attachment; filename={op.basename(self.store.model_path)}')
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
                    data = data.drop(
                        [self.store.load('target_col')], axis=1, errors='ignore'
                    )
                    prediction = yield gramex.service.threadpool.submit(
                        self._predict, data)
                    self.write(json.dumps(prediction, indent=2, cls=CustomJSONEncoder))
                else:
                    self.set_header('Content-Type', 'text/html')
                    self.render(self.template, handler=self, data=self.store.load_data())
        super(MLHandler, self).get(*path_args, **path_kwargs)

    def _append(self):
        self._parse_data(_cache=True, append=True)

    def _train(self, data=None):
        target_col = self.get_argument('target_col', self.store.load('target_col'))
        self.store.dump('target_col', target_col)
        data = self._parse_data(False) if data is None else data
        self.model = get_model(store=self.store)
        self.model.fit(data, self.store.model_path, self.name)
        return {'score': self.model.score(data, target_col)}

    def _retrain(self):
        return self._train(self.store.load_data())

    def _score(self):
        self._check_model_path()
        data = self._parse_data(False)
        target_col = self.get_argument('target_col', self.store.load('target_col'))
        self.store.dump('target_col', target_col)
        metric = self.get_argument('_metric', '')
        return {'score': self.model.score(data, target_col, metric=metric)}

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
        params = self.store.load('params', {})
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
