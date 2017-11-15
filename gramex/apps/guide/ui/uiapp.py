"""Data processing functionalities."""
from __future__ import unicode_literals

import io
import os
import json
import gramex.cache
from hashlib import md5
from tornado.gen import coroutine, Return
from gramex.config import variables


def join(*args):
    return os.path.normpath(os.path.join(*args))


folder = os.path.dirname(os.path.abspath(__file__))
config_file = join(folder, 'config.yaml')
cache_dir = join(variables['GRAMEXDATA'], 'apps', 'guide', 'ui')
bootstrap_path = join(folder, '..', 'node_modules', 'bootstrap', 'scss', 'bootstrap')
sass_path = join(folder, '..', 'node_modules', 'node-sass', 'bin', 'node-sass')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)


def process_data(handler):
    """Data processing."""
    return handler.get_argument('data')


def get_config(handler):
    '''Return config.yaml as a JSON file'''
    config = gramex.cache.open(config_file, 'config')
    return json.dumps(config, ensure_ascii=True, indent=2)


@coroutine
def bootstrap_theme(handler):
    '''
    Return a bootstrap theme based on the custom SASS variables provided.
    '''
    args = json.dumps(handler.args, sort_keys=True, ensure_ascii=True)
    cache_key = md5(args.encode('utf-8')).hexdigest()[:5]

    # Cache based on the dict and config
    config = gramex.cache.open(config_file, 'config')
    cache_path = os.path.join(cache_dir, 'bootstrap-theme.%s.css' % cache_key)
    if (not os.path.exists(cache_path) or
            os.stat(config_file).st_mtime > os.stat(cache_path).st_mtime):
        # Create a SCSS file based on the args
        scss_path = join(cache_dir, 'bootstrap-theme.%s.scss' % cache_key)
        with io.open(scss_path, 'w', encoding='utf-8') as handle:
            variables = {}
            for name, info in config['color'].items():
                variables[name] = handler.get_arg(name, info['default'])
            for name, info in config['toggle'].items():
                variables.update(info['options'][handler.get_arg(name, info['default'])])
            for name, info in config['font'].items():
                val = info['options'][handler.get_arg(name, info['default'])]
                if val['stack'] is not None:
                    variables[name] = val['stack']
                if val['google']:
                    handle.write('@import url("https://fonts.googleapis.com/css?family=%s");\n' %
                                 val['google'])
            for key, val in variables.items():
                handle.write('$%s: %s;\n' % (key, val))
            handle.write('@import "%s";\n' % bootstrap_path.replace('\\', '/'))
        # Run sass to generate the output
        proc = gramex.cache.Subprocess(['node', sass_path, scss_path, cache_path])
        out, err = yield proc.wait_for_exit()

    with io.open(cache_path, 'rb') as handle:
        raise Return(handle.read())
