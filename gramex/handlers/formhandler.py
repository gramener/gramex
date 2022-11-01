import json
import tornado.gen
import gramex.cache
import gramex.data
import pandas as pd
from orderedattrdict import AttrDict
from tornado.web import HTTPError
from gramex import conf as gramex_conf
from gramex.http import BAD_REQUEST, INTERNAL_SERVER_ERROR
from gramex.transforms import build_transform
from gramex.config import merge, app_log, objectpath, CustomJSONEncoder
from .basehandler import BaseHandler


def namespaced_args(args, namespace):
    '''
    Filter from handler.args the keys relevant for namespace, i.e. those
    prefixed with the namespace, or those without a prefix.
    '''
    if not namespace.endswith(':'):
        namespace += ':'
    result = {}
    for key, val in args.items():
        if key.startswith(namespace):
            result[key[len(namespace) :]] = val
        elif ':' not in key:
            result[key] = val
    return result


class FormHandler(BaseHandler):
    # Else there should be at least 1 key that has a url: sub-key. The data spec is at that level
    # Data spec is (url, engine, table, ext, ...) which goes directly to filter
    # It also has
    #   default: which is interpreted as argument defaults
    #   keys: defines the primary key columns

    # FormHandler function kwargs and the parameters they accept:
    function_vars = {
        'modify': {'data': None, 'key': None, 'handler': None},
        'prepare': {'args': None, 'key': None, 'handler': None},
        'queryfunction': {'args': None, 'key': None, 'handler': None},
        'state': {'args': None, 'key': None, 'handler': None},
    }
    data_filter_method = staticmethod(gramex.data.filter)

    @classmethod
    def setup(cls, **kwargs):
        super(FormHandler, cls).setup(**kwargs)
        conf_kwargs = merge(
            AttrDict(kwargs), objectpath(gramex_conf, 'handlers.FormHandler', {}), 'setdefault'
        )
        cls.headers = conf_kwargs.pop('headers', {})
        # Top level formats: key is special. Don't treat it as data
        cls.formats = conf_kwargs.pop('formats', {})
        default_config = conf_kwargs.pop('default', None)
        # Remove other known special keys from dataset configuration
        cls.clear_special_keys(conf_kwargs)
        # If top level has url: then data spec is at top level. Else it's a set of sub-keys
        if 'url' in conf_kwargs:
            cls.datasets = AttrDict(data=conf_kwargs)
            cls.single = True
        else:
            if 'modify' in conf_kwargs:
                cls.modify_all = staticmethod(
                    build_transform(
                        conf={'function': conf_kwargs.pop('modify', None)},
                        vars=cls.function_vars['modify'],
                        filename=f'{cls.name}.modify',
                        iter=False,
                    )
                )
            cls.datasets = conf_kwargs
            cls.single = False
        # Apply defaults to each key
        if isinstance(default_config, dict):
            for key in cls.datasets:
                config = cls.datasets[key].get('default', {})
                cls.datasets[key]['default'] = merge(config, default_config, mode='setdefault')
        # Ensure that each dataset is a dict with a url: key at least
        for key, dataset in list(cls.datasets.items()):
            if not isinstance(dataset, dict):
                app_log.error(f'{cls.name}: {key}: must be a dict, not {dataset!r}')
                del cls.datasets[key]
            elif 'url' not in dataset:
                app_log.error(f'{cls.name}: {key}: does not have a url: key')
                del cls.datasets[key]
            # Ensure that id: is a list -- if it exists
            if 'id' in dataset and not isinstance(dataset['id'], list):
                dataset['id'] = [dataset['id']]
            # Convert function: into a data = transform(data) function
            conf = {
                'function': dataset.pop('function', None),
                'args': dataset.pop('args', None),
                'kwargs': dataset.pop('kwargs', None),
            }
            if conf['function'] is not None:
                fn_name = f'{cls.name}.{key}.transform'
                dataset['transform'] = build_transform(
                    conf, vars={'data': None, 'handler': None}, filename=fn_name, iter=False
                )
            # Convert modify: and prepare: into a data = modify(data) function
            for fn, fn_vars in cls.function_vars.items():
                if fn in dataset:
                    dataset[fn] = build_transform(
                        conf={'function': dataset[fn]},
                        vars=fn_vars,
                        filename=f'{cls.name}.{key}.{fn}',
                        iter=False,
                    )

    def _options(self, dataset, args, path_args, path_kwargs, key):
        """For each dataset, prepare the arguments."""
        if self.request.body:
            content_type = self.request.headers.get('Content-Type', '')
            if content_type == 'application/json':
                args.update(json.loads(self.request.body))
        filter_kwargs = AttrDict(dataset)
        filter_kwargs.pop('modify', None)
        prepare = filter_kwargs.pop('prepare', None)
        queryfunction = filter_kwargs.pop('queryfunction', None)
        state = filter_kwargs.pop('state', None)
        filter_kwargs['transform_kwargs'] = {'handler': self}
        # Use default arguments
        defaults = {
            k: v if isinstance(v, list) else [v]
            for k, v in filter_kwargs.pop('default', {}).items()
        }
        # /(.*)/(.*) become 2 path arguments _0 and _1
        defaults.update({f'_{k}': [v] for k, v in enumerate(path_args)})
        # /(?P<x>\d+)/(?P<y>\d+) become 2 keyword arguments x and y
        defaults.update({k: [v] for k, v in path_kwargs.items()})
        args = merge(namespaced_args(args, key), defaults, mode='setdefault')
        if callable(prepare):
            result = prepare(args=args, key=key, handler=self)
            if result is not None:
                args = result
        if callable(queryfunction):
            filter_kwargs['query'] = queryfunction(args=args, key=key, handler=self)
        if callable(state):
            filter_kwargs['state'] = lambda: state(args=args, key=key, handler=self)
        return AttrDict(
            fmt=args.pop('_format', ['json'])[0],
            download=args.pop('_download', [''])[0],
            args=args,
            meta_header=args.pop('_meta', [''])[0],
            filter_kwargs=filter_kwargs,
        )

    @tornado.gen.coroutine
    def get(self, *path_args, **path_kwargs):
        meta, futures = AttrDict(), AttrDict()
        for key, dataset in self.datasets.items():
            meta[key] = AttrDict()
            opt = self._options(dataset, self.args, path_args, path_kwargs, key)
            opt.filter_kwargs.pop('id', None)
            # Run query in a separate threadthread
            futures[key] = gramex.service.threadpool.submit(
                self.data_filter_method, args=opt.args, meta=meta[key], **opt.filter_kwargs
            )
            # gramex.data.filter() should set the schema only on first load. Pop it once done
            dataset.pop('schema', None)
        self.pre_modify()
        result = AttrDict()
        for key, val in futures.items():
            try:
                result[key] = yield val
            except ValueError as e:
                app_log.exception(f'{self.name}: filter failed')
                raise HTTPError(BAD_REQUEST, e.args[0])
            except Exception as e:
                app_log.exception(f'{self.name}: filter failed')
                raise HTTPError(INTERNAL_SERVER_ERROR, repr(e))
            modify = self.datasets[key].get('modify', None)
            if callable(modify):
                result[key] = modify(data=result[key], key=key, handler=self)

        # modify the result for multiple datasets
        if hasattr(self, 'modify_all'):
            result = self.modify_all(data=result, key=None, handler=self)

        # Note: Don't redirect GET. They should only be used to get data, not for side-effects.
        # Allowing redirect has no purpose except for side-effects.
        self.render_result(opt, meta, result, redirect=False)

    def render_result(self, opt, meta, result, redirect=True):
        format_options = self.set_format(opt.fmt, meta)
        format_options['args'] = opt.args
        params = {k: v[0] for k, v in opt.args.items() if len(v) > 0}
        for key, val in format_options.items():
            if isinstance(val, str):
                format_options[key] = val.format(**params)
            # In PY2, the values are binary. TODO: ensure that format values are in Unicode
            elif isinstance(val, bytes):
                format_options[key] = val.decode('utf-8').format(**params)
        if opt.download:
            self.set_header('Content-Disposition', f'attachment;filename={opt.download}')
        if opt.meta_header:
            self.set_meta_headers(meta)
        result = result['data'] if self.single else result
        # If modify has changed the content type from a dataframe, write it as-is
        if isinstance(result, (pd.DataFrame, dict)):
            self.write(gramex.data.download(result, **format_options))
        elif result:
            self.write(result)
        if redirect and self.redirects:
            self.redirect_next()

    @tornado.gen.coroutine
    def update(self, method, *path_args, **path_kwargs):
        if self.redirects:
            self.save_redirect_page()
        meta, result = AttrDict(), AttrDict()
        # For each dataset
        for key, dataset in self.datasets.items():
            meta[key] = AttrDict()
            opt = self._options(dataset, self.args, path_args, path_kwargs, key)
            if 'id' not in opt.filter_kwargs:
                raise HTTPError(
                    BAD_REQUEST, f'{self.name}: need id: in kwargs: to {self.request.method}'
                )
            missing_args = [col for col in opt.filter_kwargs['id'] if col not in opt.args]
            if method != gramex.data.insert and len(missing_args) > 0:
                raise HTTPError(
                    BAD_REQUEST,
                    f'{self.name}: missing column(s) in URL query: ' + ', '.join(missing_args),
                )
            # Execute the query. This returns the count of records updated
            result[key] = method(meta=meta[key], args=opt.args, **opt.filter_kwargs)
            # method() should set the schema only on first load. Pop it once done
            dataset.pop('schema', None)
        self.pre_modify()
        for key, val in result.items():
            modify = self.datasets[key].get('modify', None)
            if callable(modify):
                meta[key]['modify'] = modify(data=result[key], key=key, handler=self)
            self.set_header(f'Count-{key}', val)
        # modify the result for multiple datasets
        if hasattr(self, 'modify_all'):
            meta['modify'] = self.modify_all(data=result, key=None, handler=self)

        self.set_header('Cache-Control', 'no-cache, no-store')
        self.render_result(opt, meta, {'data': meta} if self.single else meta, redirect=True)

    @tornado.gen.coroutine
    def delete(self, *path_args, **path_kwargs):
        yield self.update(gramex.data.delete, *path_args, **path_kwargs)

    @tornado.gen.coroutine
    def post(self, *path_args, **path_kwargs):
        yield self.update(gramex.data.insert, *path_args, **path_kwargs)

    @tornado.gen.coroutine
    def put(self, *path_args, **path_kwargs):
        yield self.update(gramex.data.update, *path_args, **path_kwargs)

    def set_format(self, fmt, meta):
        # Identify format to render in. The default format, json, is defined in
        # the base gramex.yaml under handlers.FormHandler.formats
        if fmt in self.formats:
            fmt = dict(self.formats[fmt])
        else:
            app_log.error(f'{self.name}: _format={fmt} unknown. Using _format=json')
            fmt = dict(self.formats['json'])

        # Set up default headers, and over-ride with headers for the format
        for key, val in self.headers.items():
            self.set_header(key, val)
        for key, val in fmt.pop('headers', {}).items():
            self.set_header(key, val)

        if fmt['format'] in {'template', 'pptx', 'vega', 'vega-lite', 'vegam'}:
            fmt['handler'] = self
        if fmt['format'] in {'template'}:
            fmt['meta'] = meta['data'] if self.single else meta

        return fmt

    def set_meta_headers(self, meta):
        '''Add FH-<dataset>-<key>: JSON(value) for each key: value in meta'''
        prefix = 'FH-{}-{}'
        for dataset, metadata in meta.items():
            for key, value in metadata.items():
                string_value = json.dumps(
                    value, separators=(',', ':'), ensure_ascii=True, cls=CustomJSONEncoder
                )
                self.set_header(prefix.format(dataset, key), string_value)

    def pre_modify(self, **kwargs):
        '''Called after inserting records into DB. Subclasses use it for additional processing'''
        pass
