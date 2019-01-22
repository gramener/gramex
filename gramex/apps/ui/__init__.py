'''Main UI application'''
from __future__ import unicode_literals

import io
import os
import json
import gramex.cache
from hashlib import md5
from tornado.gen import coroutine, Return
from gramex.config import variables, app_log, merge


def join(*args):
    return os.path.normpath(os.path.join(*args))


folder = os.path.dirname(os.path.abspath(__file__))
config_file = join(folder, 'config.yaml')
uicomponents_path = join(folder, 'bootstrap-theme.scss')
cache_dir = join(variables['GRAMEXDATA'], 'apps', 'ui')
bootstrap_path = join(folder, 'node_modules', 'bootstrap', 'scss', 'bootstrap')
sass_path = join(folder, 'node_modules', 'node-sass', 'bin', 'node-sass')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)


@coroutine
def sass(handler, template=uicomponents_path):
    '''
    Return a bootstrap theme based on the custom SASS variables provided.
    '''
    args = dict(variables.get('ui-bootstrap', {}))
    args.update({key: handler.get_arg(key) for key in handler.args})
    args = {key: val for key, val in args.items() if val}

    # Set default args
    config = gramex.cache.open(config_file)
    merge(args, config.get('defaults'), mode='setdefault')

    cache_key = {'template': template, 'args': args}
    cache_key = json.dumps(
        cache_key, sort_keys=True, ensure_ascii=True).encode('utf-8')
    cache_key = md5(cache_key).hexdigest()[:5]

    # Replace fonts from config file, if available
    google_fonts = set()
    for key in ('font-family-base', 'headings-font-family'):
        if key in args and args[key] in config['fonts']:
            fontinfo = config['fonts'][args[key]]
            args[key] = fontinfo['stack']
            if 'google' in fontinfo:
                google_fonts.add(fontinfo['google'])

    # Cache based on the dict and config as template.<cache-key>.css
    base = os.path.splitext(os.path.basename(template))[0] + '.' + cache_key
    cache_path = join(cache_dir, base + '.css')
    if not os.path.exists(cache_path) or os.stat(template).st_mtime > os.stat(cache_path).st_mtime:
        # Create a SCSS file based on the args
        scss_path = join(cache_dir, base + '.scss')
        with io.open(scss_path, 'wb') as handle:
            result = gramex.cache.open(template, 'template').generate(
                variables=args,
                uicomponents_path=uicomponents_path.replace('\\', '/'),
                bootstrap_path=bootstrap_path.replace('\\', '/'),
                google_fonts=google_fonts,
            )
            handle.write(result)
        # Run sass to generate the output
        options = ['--output-style', 'compressed']
        proc = gramex.cache.Subprocess(
            ['node', sass_path, scss_path, cache_path] + options)
        out, err = yield proc.wait_for_exit()
        if proc.proc.returncode:
            app_log.error('node-sass error: %s', err)
            raise RuntimeError('Compilation failure')

    handler.set_header('Content-Type', 'text/css')
    raise Return(gramex.cache.open(cache_path, 'bin', mode='rb'))
