from fnmatch import fnmatch
import inspect
import json
import re
import gramex
import gramex.cache
from typing import get_type_hints
from textwrap import dedent
from gramex.config import merge
from gramex.transforms.transforms import typelist, Header
from gramex.handlers import BaseHandler

config = gramex.cache.open('openapiconfig.yaml', 'config', rel=True)


def url_name(pattern):
    # Spec name is the last URL path that has alphabets
    names = [part for part in pattern.split('/') if any(c.isalnum() for c in part)]
    # Capitalize. url-like_this becomes "Url Like This"
    names = [word.capitalize() for word in re.split(r'[\s\-_]', ' '.join(names))]
    return ' '.join(names)


class OpenAPIHandler(BaseHandler):
    types = {str: 'string', int: 'integer', float: 'number', bool: 'boolean', None: 'null'}

    @classmethod
    def function_spec(cls, function):
        params = []
        spec = {
            'description': dedent(getattr(function, '__doc__', '') or ''),
            'parameters': params,
        }
        # Get the function signature. But "function: str" fails with ValueError.
        # In such cases, skip the parameter configuration.
        try:
            signature = inspect.signature(function)
        except ValueError:
            return spec
        hints = get_type_hints(function)
        for name, param in signature.parameters.items():
            hint = hints.get(name, None)
            typ, is_list = typelist(hints[name]) if hint else (str, False)
            conf = {
                'in': 'header' if hint and hint is Header else 'query',
                'name': name,
                'description': getattr(param.annotation, '__metadata__', ('',))[0],
                'schema': {},
            }
            params.append(conf)
            # If default is not specific, parameter is required.
            if param.default is inspect.Parameter.empty:
                conf['required'] = True
            else:
                conf['schema']['default'] = param.default
            # JSON Schema uses {type: array, items: {type: integer}} for array of ints.
            # But a simple int is {type: integer}
            if is_list:
                conf['schema']['type'] = 'array'
                conf['schema']['items'] = {'type': cls.types.get(typ, 'string')}
            else:
                conf['schema']['type'] = cls.types.get(typ, 'string')
        spec['responses'] = config.responses
        return spec

    def formhandler_spec(self, cls, summary):
        spec = {}
        datasets = getattr(cls, 'datasets', {})
        get_spec = spec['get'] = {
            'summary': summary,
            # TODO: Document type of data source
            'description': f'Query data from {len(datasets)} data source(s)',
        }
        params = get_spec['parameters'] = []
        for name, dataset in datasets.items():

            def add(param, **keys):
                param = merge({}, param)
                params.append(
                    merge(
                        param,
                        {
                            'name': param['name'] if cls.single else f'{name}:{param["name"]}',
                            **keys,
                        },
                    )
                )

            # For every column, add
            #   ?_c=<col>
            #   ?_sort=<col> and ?_sort=-<col>
            #   ?<col>=
            cols, sorts = [], []
            for col in dataset.get('columns', []):
                if isinstance(col, dict):
                    add(config.formhandler.col, name=col['name'], schema={'type': col['type']})
                    cols.append(col['name'])
                    sorts.append(col['name'])
                    sorts.append('-' + col['name'])
                else:
                    add(config.formhandler.col, name=col)
                    cols.append(col)
                    sorts.append(col)
                    sorts.append('-' + col)
            add(config.formhandler._sort, schema={'items': {'enum': sorts}})
            add(config.formhandler._c, schema={'items': {'enum': cols}})
            add(config.formhandler._offset)
            add(config.formhandler._limit)
            add(config.formhandler._meta)
        # TODO: If ID is present, allow GET, POST, DELETE. Else only GET
        get_spec['responses'] = config.responses
        return spec

    def get(self):
        kwargs = self.conf.get('kwargs', {})
        # TODO: Set header only if not already set in the configuration.
        # This can be handled in gramex/gramex.yaml as a default configuration.
        # Switch to YAML if a YAML spec is requested
        self.set_header('Content-Type', 'application/json')

        spec = {
            'openapi': '3.0.2',
            'info': kwargs.get('info', {}),
            'servers': kwargs.get('servers', {}),
            'paths': {},
        }

        key_patterns = kwargs.get('urls', ['*'])
        # Loop through every function and get the default specs
        for key, config in gramex.conf['url'].items():
            # Only pick up those keys that matches the key pattern.
            # Since imports create subkeys joined with :, just use the last part
            key_end = key.split(':')[-1]
            if not any(fnmatch(key_end, pat) for pat in key_patterns):
                continue
            # Ignore invalid handlers
            if key not in gramex.service.url or 'handler' not in config or 'pattern' not in config:
                continue
            # Normalize the pattern, e.g. /./docs -> /docs
            pattern = config['pattern'].replace('/./', '/')
            summary = f'{url_name(pattern)}: {config["handler"]}'
            # TODO: Handle wildcards, e.g. /(.*) -> / with an arg
            info = spec['paths'][pattern] = {
                'get': {'summary': summary},
            }
            cls = gramex.service.url[key].handler_class
            if issubclass(cls, gramex.handlers.FunctionHandler):
                # Ignore functions with invalid setup
                if not hasattr(cls, 'info') or 'function' not in cls.info:
                    continue
                function = cls.info['function']
                function = getattr(function, '__func__', None) or function
                if callable(function):
                    fnspec = self.function_spec(function)
                    fnspec['summary'] = summary
                    default_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
                    for method in getattr(cls, '_http_methods', default_methods):
                        info[method.lower()] = fnspec
            elif issubclass(cls, gramex.handlers.FormHandler):
                info.update(self.formhandler_spec(cls, summary=summary))
            # User's spec definition overrides our spec definition
            merge(info, cls.conf.get('openapi', {}), mode='overwrite')

        args = self.argparse(indent={'type': int, 'default': 0})
        self.write(
            json.dumps(
                spec,
                indent=args.indent or None,
                separators=(', ', ': ') if args.indent else (',', ':'),
            )
        )
