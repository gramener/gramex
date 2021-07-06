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
vue_path = join(ui_dir, 'node_modules', '@vue', 'cli', 'bin', 'vue')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)


def get_cache_key(state):
    cache_key = json.dumps(state, sort_keys=True, ensure_ascii=True).encode('utf-8')
    return md5(cache_key).hexdigest()[:5]


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

    cache_key = get_cache_key({'template': template, 'args': args})

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
            raise RuntimeError('node-sass compilation failure', err.decode('utf-8'))

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
    cache_key = get_cache_key([path, commands, vars])
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
            raise RuntimeError('node-sass compilation failure', proc.stderr)

    handler.set_header('Content-Type', 'text/css')
    return gramex.cache.open(cache_file, 'bin', mode='rb')


@coroutine
def vue(handler, path: str):
    '''Compile a .vue file'''
    # Get valid variables from URL query parameters
    # Create cache key based on state = path. Output to <cache-key>.js
    path = os.path.normpath(path).replace('\\', '/')
    cache_key = get_cache_key([path])
    target_dir = join(cache_dir, f'vue-{cache_key}')

    # Recompile if output cache_file is missing, or path has been updated
    if not os.path.exists(target_dir) or os.stat(path).st_mtime > os.stat(target_dir).st_mtime:
        # Compile Vue file
        cwd, filename = os.path.split(path)

        proc = yield gramex.service.threadpool.submit(subprocess.run, [
            # unhandled-rejections ensures that returncode != 0 on error
            'node', '--unhandled-rejections=strict',
            vue_path, 'build', '--target', 'wc', filename, '--dest', target_dir
        ], cwd=cwd, capture_output=True, encoding='utf-8')
        print(' '.join([
            # unhandled-rejections ensures that returncode != 0 on error
            'node', '--unhandled-rejections=strict',
            vue_path, 'build', '--target', 'wc', filename, '--dest', target_dir
        ]))
        if proc.returncode:
            raise RuntimeError(f'Vue compilation failure:\n{proc.stderr}')

    source = os.path.split(path)[-1]
    target = os.path.split(path)[-1].replace('.vue', '.min.js')
    if 'map' in handler.args:
        # Serve map file if browser requested component-name.vue?map
        handler.set_header('Content-Type', 'application/json')
        return gramex.cache.open(os.path.join(target_dir, target + '.map'), 'bin', mode='rb')
    else:
        # Serve compiled JS if browser requested just .vue
        handler.set_header('Content-Type', 'text/javascript')
        content = gramex.cache.open(os.path.join(target_dir, target), 'bin', mode='rb')
        # ... but replace the map file with component-name.vue?map
        return content.replace(
            f'//# sourceMappingURL={target}.map'.encode('utf-8'),
            f'//# sourceMappingURL={source}?map'.encode('utf-8'))

# Test cases
# - Invalid Vue file should generate a compilation failure
# - Changing Vue file should recompile
