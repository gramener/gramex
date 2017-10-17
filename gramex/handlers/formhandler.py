from __future__ import unicode_literals

import tornado.gen
import gramex.cache
import gramex.data
from orderedattrdict import AttrDict
from tornado.web import HTTPError
from gramex import conf as gramex_conf
from gramex.http import BAD_REQUEST
from gramex.transforms import build_transform
from gramex.config import merge, app_log, objectpath
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
            result[key[len(namespace):]] = val
        elif ':' not in key:
            result[key] = val
    return result


class FormHandler(BaseHandler):
    '''
    # Else there should be at least 1 key that has a url: sub-key. The data spec is at that level
    # Data spec is (url, engine, table, ext, ...) which goes directly to filter
    # It also has
    #   default: which is interpreted as argument defaults
    #   keys: defintes the primary key columns
    '''
    # FormHandler function kwargs and the parameters they accept:
    function_vars = {
        'modify': {'data': None, 'key': None, 'handler': None},
        'prepare': {'args': None, 'key': None, 'handler': None},
        'queryfunction': {'args': None, 'key': None, 'handler': None},
    }

    @classmethod
    def setup(cls, **kwargs):
        super(FormHandler, cls).setup(**kwargs)
        merge(cls.conf.kwargs,
              objectpath(gramex_conf, 'handlers.FormHandler', {}),
              mode='setdefault')
        # Top level formats: key is special. Don't treat it as data
        cls.formats = cls.conf.kwargs.pop('formats', {})
        # If top level has url: then data spec is at top level. Else it's a set of sub-keys
        if 'url' in cls.conf.kwargs:
            cls.datasets = {'data': cls.conf.kwargs}
            cls.single = True
        else:
            cls.datasets = cls.conf.kwargs
            cls.single = False
        # Ignore special keys. default: updates the args, and cannot be a dataset key
        default_config = cls.datasets.pop('default', None)
        if isinstance(default_config, dict):
            for key in cls.datasets:
                config = cls.datasets[key].get('default', {})
                cls.datasets[key]['default'] = merge(config, default_config, mode='setdefault')
        # Ensure that each dataset is a dict with a url: key at least
        for key, dataset in list(cls.datasets.items()):
            if not isinstance(dataset, dict):
                app_log.error('%s: %s: must be a dict, not %r' % (cls.name, key, dataset))
                del cls.datasets[key]
            elif 'url' not in dataset:
                app_log.error('%s: %s: does not have a url: key' % (cls.name, key))
                del cls.datasets[key]
            # Convert function: into a data = transform(data) function
            conf = {
                'function': dataset.pop('function', None),
                'args': dataset.pop('args', None),
                'kwargs': dataset.pop('kwargs', None)
            }
            if conf['function'] is not None:
                fn_name = '%s.%s.transform' % (cls.name, key)
                dataset['transform'] = build_transform(
                    conf, vars={'data': None}, filename=fn_name, iter=False)
            # Convert modify: and prepare: into a data = modify(data) function
            for fn, fn_vars in cls.function_vars.items():
                if fn in dataset:
                    dataset[fn] = build_transform(
                        conf={'function': dataset[fn]},
                        vars=fn_vars,
                        filename='%s.%s.%s' % (cls.name, key, fn), iter=False)

    @tornado.gen.coroutine
    def get(self):
        meta, futures = AttrDict(), AttrDict()
        for key, dataset in self.datasets.items():
            meta[key] = AttrDict()
            filter_kwargs = AttrDict(dataset)
            filter_kwargs.pop('modify', None)
            prepare = filter_kwargs.pop('prepare', None)
            queryfunction = filter_kwargs.pop('prepare', None)
            defaults = {
                key: val if isinstance(val, list) else [val]
                for key, val in filter_kwargs.pop('default', {}).items()
            }
            args = merge(namespaced_args(self.args, key), defaults, mode='setdefault')
            if callable(prepare):
                result = prepare(args=args, key=key, handler=self)
                if result is not None:
                    args = result
            if callable(queryfunction):
                filter_kwargs['query'] = queryfunction(args=args, key=key, handler=self)
            # Run query in a separate thread
            futures[key] = gramex.service.threadpool.submit(
                gramex.data.filter, args=args, meta=meta[key], **filter_kwargs)
        result = AttrDict()
        for key, val in futures.items():
            try:
                result[key] = yield val
            except ValueError as e:
                raise HTTPError(BAD_REQUEST, reason=e.args[0])
            modify = self.datasets[key].get('modify', None)
            if callable(modify):
                result[key] = modify(data=result[key], key=key, handler=self)

        # Identify format to render in. The default format, json, is defined in
        # the base gramex.yaml under handlers.FormHandler.formats
        fmt = args.get('_format', ['json'])[0]
        if fmt in self.formats:
            fmt = dict(self.formats[fmt])
        else:
            app_log.error('%s: _format=%s unknown. Using _format=json' % (self.name, fmt))
            fmt = dict(self.formats['json'])

        # Set up headers for the format
        headers = fmt.pop('headers', {})
        for key, val in headers.items():
            self.set_header(key, val)

        if fmt['format'] == 'template':
            fmt['handler'] = self
            fmt['meta'] = meta['data'] if self.single else meta

        self.write(gramex.data.download(result['data'] if self.single else result, **fmt))
