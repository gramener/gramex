from fnmatch import fnmatch
import inspect
import json
import re
import gramex
from typing import get_type_hints
from textwrap import dedent
from gramex.config import merge
from gramex.transforms.transforms import typelist, Header
from gramex.handlers import BaseHandler

error_codes = {
    '200': {
        'description': 'Successful Response',
        'content': {'application/json': {}}
    },
    '400': {
        'description': 'Bad request',
        'content': {'text/html': {'example': 'Bad request'}}
    },
    '401': {
        'description': 'Not authorized',
        'content': {'text/html': {'example': 'Not authorized'}}
    },
    '403': {
        'description': 'Forbidden',
        'content': {'text/html': {'example': 'Forbidden'}}
    },
    '404': {
        'description': 'Not found',
        'content': {'text/html': {'example': 'Not found'}}
    },
    '500': {
        'description': 'Internal server error',
        'content': {'text/html': {'example': 'Internal server error'}}
    },
}


def url_name(pattern):
    # Spec name is the last URL path that has alphabets
    names = [part for part in pattern.split('/') if any(c.isalnum() for c in part)]
    # Capitalize. url-like_this becomes "Url Like This"
    names = [word.capitalize() for word in re.split(r'[\s\-_]', ' '.join(names))]
    return ' '.join(names)


class OpenAPIHandler(BaseHandler):
    types = {
        str: 'string',
        int: 'integer',
        float: 'number',
        bool: 'boolean',
        None: 'null'
    }

    @classmethod
    def function_spec(cls, function):
        params = []
        spec = {
            'description': dedent(getattr(function, '__doc__', '') or ''),
            'parameters': params
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
            config = {
                'in': 'header' if hint and hint is Header else 'query',
                'name': name,
                'description': getattr(param.annotation, '__metadata__', ('',))[0],
                'schema': {}
            }
            params.append(config)
            # If default is not specific, parameter is required.
            if param.default is inspect.Parameter.empty:
                config['required'] = True
            else:
                config['default'] = param.default
            # JSON Schema uses {type: array, items: {type: integer}} for array of ints.
            # But a simple int is {type: integer}
            if is_list:
                config['schema']['type'] = 'array'
                config['schema']['items'] = {'type': cls.types.get(typ, 'string')}
            else:
                config['schema']['type'] = cls.types.get(typ, 'string'),
        spec['responses'] = error_codes
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
            'paths': {}
        }

        key_patterns = kwargs.get('urls', ['*'])
        # Loop through every function and get the default specs
        for key, config in gramex.conf['url'].items():
            # Only pick up those keys that matches the key pattern.
            # Since imports create subkeys joined with :, just use the last part
            key_end = key.split(':')[-1]
            if not any(fnmatch(key_end, pat) for pat in key_patterns):
                continue
            # Normalize the pattern, e.g. /./docs -> /docs
            pattern = config['pattern'].replace('/./', '/')
            # Ignore invalid handlers
            if key not in gramex.service.url or 'handler' not in config:
                continue
            # TODO: Handle wildcards, e.g. /(.*) -> / with an arg
            info = spec['paths'][pattern] = {
                'get': {
                    'summary': f'{url_name(pattern)}: {config["handler"]}'
                },
            }
            cls = gramex.service.url[key].handler_class
            if config['handler'] == 'FunctionHandler':
                # Ignore functions with invalid setup
                if hasattr(cls, 'info') and 'function' in cls.info:
                    function = cls.info['function']
                    function = function.__func__ or function
                    if callable(function):
                        fnspec = self.function_spec(function)
                        fnspec['summary'] = f'{url_name(pattern)}: {config["handler"]}'
                        default_methods = 'GET POST PUT DELETE PATCH OPTIONS'.split()
                        for method in getattr(cls, '_http_methods', default_methods):
                            info[method.lower()] = fnspec
            # User's spec definition overrides our spec definition
            merge(info, cls.conf.get('openapi', {}), mode='overwrite')

        args = self.argparse(indent={'type': int, 'default': 0})
        self.write(json.dumps(
            spec,
            indent=args.indent or None,
            separators=(', ', ': ') if args.indent else (',', ':'),
        ))
