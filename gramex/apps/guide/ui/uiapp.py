"""Data processing functionalities."""
from __future__ import unicode_literals

import io
import os
import json
from hashlib import md5
from tornado.gen import coroutine, Return
from gramex.cache import Subprocess
from gramex.config import variables, merge


def join(*args):
    return os.path.normpath(os.path.join(*args))


folder = os.path.dirname(os.path.abspath(__file__))
cache_dir = join(variables['GRAMEXDATA'], 'apps', 'guide', 'ui')
bootstrap_path = join(folder, '..', 'node_modules', 'bootstrap', 'scss', 'bootstrap')
scss_path = join(cache_dir, 'bootstrap-theme.scss')
sass_path = join(folder, '..', 'node_modules', 'node-sass', 'bin', 'node-sass')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
style_vars = {
    'enable-rounded',
    'enable-shadows',
    'enable-gradients',
    'enable-transitions',
    'enable-print-styles',
}


def process_data(handler):
    """Data processing."""
    return handler.get_argument('data')


@coroutine
def bootstrap_theme(handler):
    '''
    Return a bootstrap theme based on the custom SASS variables provided.
    '''
    args = json.dumps(handler.args, sort_keys=True, ensure_ascii=True)
    cache_key = md5(args.encode('utf-8')).hexdigest()[:5]

    # Cache based on the dict
    cache_path = os.path.join(cache_dir, 'bootstrap-theme.%s.css' % cache_key)
    if True or not os.path.exists(cache_path):
        # Create a SCSS file based on the dict
        with io.open(scss_path, 'w', encoding='utf-8') as handle:
            variables = {
                key: 'true' if val[0] == 'on' else val[0]
                for key, val in handler.args.items()
            }
            # If any query parameters are passed, ensure that checkbox parameters
            # default to false
            if len(handler.args):
                merge(variables, {key: 'false' for key in style_vars}, 'setdefault')
            for key, val in variables.items():
                handle.write('$%s: %s;\n' % (key, val))
            handle.write('@import "%s";\n' % bootstrap_path.replace('\\', '/'))
        # Run sass to generate the output
        yield Subprocess(['node', sass_path, scss_path, cache_path]).wait_for_exit()
        os.remove(scss_path)

    with io.open(cache_path, 'rb') as handle:
        raise Return(handle.read())
