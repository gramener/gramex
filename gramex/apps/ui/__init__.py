'''Main UI application'''
import io
import re
import os
import json
import gramex
import gramex.cache
import subprocess
from hashlib import md5
from tornado.gen import coroutine, Return
from gramex.config import variables, app_log, merge


def join(*args):
    return os.path.normpath(os.path.join(*args))


ui_dir = os.path.dirname(os.path.abspath(__file__))
config_file = join(ui_dir, 'config.yaml')
cache_dir = join(variables['GRAMEXDATA'], 'apps', 'ui')
sass_path = join(ui_dir, 'node_modules', 'node-sass', 'bin', 'node-sass')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)


@coroutine
def sass(handler, template=join(ui_dir, 'bootstrap-theme.scss')):
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
                google_fonts=google_fonts,
            )
            handle.write(result)
        # Run sass to generate the output
        proc = gramex.cache.Subprocess([
            'node', sass_path, scss_path, cache_path,
            '--output-style', 'compressed',
            # Allow importing path from these paths
            '--include-path', os.path.dirname(template),
            '--include-path', ui_dir,
            '--include-path', bootstrap_dir,
        ])
        out, err = yield proc.wait_for_exit()
        if proc.proc.returncode:
            app_log.error('node-sass error: %s', err.decode('utf-8'))
            raise RuntimeError('Compilation failure')

    handler.set_header('Content-Type', 'text/css')
    raise Return(gramex.cache.open(cache_path, 'bin', mode='rb'))


bootstrap_dir = join(ui_dir, 'node_modules', 'bootstrap', 'scss')
# We only allow alphanumeric SASS keys (though SASS allows more)
valid_sass_key = re.compile(r'[_a-zA-Z][_a-zA-Z0-9\-]*')


@coroutine
def sass2(handler, path: str = join(ui_dir, 'gramexui.scss')):
    '''
    Compile a SASS file using custom variables from URL query parameters.
    The special variables ``@import``, ``@use`` and ``@forward`` can be a str/list of URLs or
    libraries to import.
    '''
    # Get valid variables from URL query parameters
    vars, commands, theme_colors = {}, {}, []
    for key, vals in handler.args.items():
        if key in {'@import', '@use', '@forward'}:
            commands[key] = vals
        # Allow only alphanumeric SASS keys
        elif not valid_sass_key.match(key):
            app_log.warning('sass: "${key}" key not allowed. Use alphanumeric')
        # Pick the last arg, if it's non-empty
        elif len(vals) and vals[-1]:
            vars[key] = vals[-1]
            # ?color-alpha=red creates theme colors like .bg-alpha, .text-alpha, etc.
            # color_ is also supported for Python keyword arguments
            if key.startswith('color-') or key.startswith('color_'):
                theme_colors.append(f'"{key[6:]}": ${key}')
    if theme_colors:
        vars['theme-colors'] = f'({", ".join(theme_colors)})'

    # Create cache key based on state = path + imports + args. Output to <cache-key>.css
    path = os.path.normpath(path).replace('\\', '/')
    state = [path, commands, vars]
    cache_key = json.dumps(state, sort_keys=True, ensure_ascii=True).encode('utf-8')
    cache_key = md5(cache_key).hexdigest()[:8]
    cache_file = join(cache_dir, f'theme-{cache_key}.css')

    # Recompile if output cache_file is missing, or path has been updated
    if not os.path.exists(cache_file) or os.stat(path).st_mtime > os.stat(cache_file).st_mtime:
        # Create an SCSS file
        scss_path = cache_file[:-4] + '.scss'
        # ... whose contents include all variables
        content = [f'${key}: {val};' for key, val in vars.items()]
        # ... and commands @import, @use, @forward (convert \ to / to handle Windows paths)
        content += [
            '%s "%s";' % (key, url.replace('\\', '/'))
            for key, urls in commands.items()
            for url in urls]
        # ... and the main SCSS file we want to use
        content.append(f'@import "{path}";')
        with open(scss_path, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(content))
        # Compile SASS file. Allow @import from template dir, UI dir, Bootstrap dir
        proc = yield gramex.service.threadpool.submit(subprocess.run, [
            'node', sass_path, scss_path, cache_file,
            '--output-style', 'compressed',
            '--include-path', os.path.dirname(path),
            '--include-path', ui_dir,
            '--include-path', bootstrap_dir,
        ], capture_output=True, input='\n'.join(content), encoding='utf-8')
        if proc.returncode:
            app_log.error('node-sass error: %s', proc.stderr)
            raise RuntimeError('Compilation failure')

    handler.set_header('Content-Type', 'text/css')
    return gramex.cache.open(cache_file, 'bin', mode='rb')
