'''Main UI application'''
import io
import re
import os
import json
import gramex
import gramex.cache
import gramex.handlers
import string

# B404:import_subprocess only for JS compilation
import subprocess  # nosec B404
from hashlib import md5
from tornado.gen import coroutine, Return
from functools import partial
from gramex.config import variables, app_log, merge
from urllib.parse import urlparse, parse_qs, urlencode


def _join(*args):
    return os.path.normpath(os.path.join(*args))


ui_dir = os.path.dirname(os.path.abspath(__file__))
config_file = _join(ui_dir, 'config.yaml')
cache_dir = _join(variables['GRAMEXDATA'], 'apps', 'ui')
sass_bin = _join(ui_dir, 'node_modules', 'sass', 'sass.js')
ts_path = _join(ui_dir, 'node_modules', 'typescript', 'bin', 'tsc')
vue_path = _join(ui_dir, 'node_modules', '@vue', 'cli-service', 'bin', 'vue-cli-service')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)


def cdn_redirect(handler, folder_map={}):
    '''Redirect /ui/... to cdn.jsdelivr.net/npm/...

    Before Gramex 1.84, specific npm libraries were included in Gramex. Now, we encourage projects
    to specify their own npm dependencies. This redirection makes apps backward compatible.

    By default, the path `/d3/dist/d3.min.js` is redirected to
    <https://cdn.jsdelivr.net/npm/d3/dist/d3.min.js>. But `folder_map` (specified in
    `gramex/apps/ui/gramex.yaml`) provides a mapping of folder names used earlier in Gramex to
    specific libraries, e.g. `{'d3v5': 'd3@5'}`.

    It redirects temporarily (HTTP 302). Add `?v=...` to URL for permanent redirection (HTTP 301).
    '''
    path = handler.path_args[0]
    for prefix, sub in folder_map.items():
        if path == prefix or path.startswith(prefix + '/'):
            path = sub + path[len(prefix) :]
            break
    handler.redirect(f'https://cdn.jsdelivr.net/npm/{path}', permanent=handler.get_arg('v', None))


def _get_cache_key(state):
    '''Return short string capturing state of object. Used to create unique filenames for state'''
    cache_key = json.dumps(state, sort_keys=True, ensure_ascii=True).encode('utf-8')
    # B324:md5 is safe here - it's not for cryptographic use
    return md5(cache_key).hexdigest()[:5]  # nosec B324


@coroutine
def sass(
    handler: gramex.handlers.FileHandler, template: str = _join(ui_dir, 'bootstrap-theme.scss')
):
    '''Return a bootstrap theme based on the custom SASS variables provided.'''
    args = dict(variables.get('ui-bootstrap', {}))
    args.update({key: handler.get_arg(key) for key in handler.args})
    args = {key: val for key, val in args.items() if val}

    # Set default args
    config = gramex.cache.open(config_file)
    merge(args, config.get('defaults'), mode='setdefault')

    cache_key = _get_cache_key({'template': template, 'args': args})

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
    cache_file = _join(cache_dir, base + '.css')
    if not os.path.exists(cache_file) or os.stat(template).st_mtime > os.stat(cache_file).st_mtime:
        # Create a SCSS file based on the args
        scss_path = _join(cache_dir, base + '.scss')
        with io.open(scss_path, 'wb') as handle:
            result = gramex.cache.open(template, 'template').generate(
                variables=args,
                google_fonts=google_fonts,
            )
            handle.write(result)
        # Run sass to generate the output
        proc = gramex.cache.Subprocess(
            [
                'node',
                sass_bin,
                scss_path,
                cache_file,
                '--style',
                'compressed',
                # Allow importing path from these paths
                '--load-path',
                os.path.dirname(template),
                '--load-path',
                ui_dir,
                '--load-path',
                bootstrap_dir,
            ]
        )
        out, err = yield proc.wait_for_exit()
        if proc.proc.returncode:
            raise RuntimeError('sass compilation failure', err.decode('utf-8'))

    handler.set_header('Content-Type', 'text/css')
    raise Return(gramex.cache.open(cache_file, 'bin', mode='rb'))


bootstrap_dir = _join(ui_dir, 'node_modules', 'bootstrap', 'scss')
# We only allow alphanumeric SASS keys (though SASS allows more)
valid_sass_key = re.compile(r'[_a-zA-Z][_a-zA-Z0-9\-]*')


@coroutine
def sass2(
    handler: gramex.handlers.FileHandler, path: str = _join(ui_dir, 'gramexui.scss')
) -> bytes:
    '''Compile a SASS file using custom variables from URL query parameters.

    Examples:
        >>> sass2(handler, 'x.sass')

    Parameters:

        handler: the[FileHandler][gramex.handlers.FileHandler] serving this file
        path: absolute path of input SASS file to compile into CSS

    Returns:

        compiled CSS file or source map if ?_map is specified

    URL query parameters in `handler.args` are converted into SASS variables.
    For example, `?primary=red` becomes `primary: red;` at the start of the SASS file.

    You can specify
    [`?@import=`](https://sass-lang.com/documentation/at-rules/import),
    [`?@use=`](https://sass-lang.com/documentation/at-rules/use) and
    [`?@forward=`](https://sass-lang.com/documentation/at-rules/forward)
    with 1 or more URLs. These URLs are imported as libraries.
    '''
    # Get valid variables from URL query parameters
    vars, commands, theme_colors = {}, {}, []
    for key, vals in handler.args.items():
        if key in {'@import', '@use', '@forward'}:
            commands[key] = vals
        # Ignore ?_map which is used for sourceMappingURL
        elif key == '_map':
            pass
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
    cache_key = _get_cache_key([path, commands, vars])
    target = _join(cache_dir, f'theme-{cache_key}.css')
    source = target[:-4] + '.scss'

    # Recompile if target is missing, or path has been updated
    if not os.path.exists(target) or os.stat(path).st_mtime > os.stat(target).st_mtime:
        # Create an SCSS file
        # ... whose contents include all variables
        content = [f'${key}: {val};' for key, val in vars.items()]
        # ... and commands @import, @use, @forward (convert \ to / to handle Windows paths)
        content += [
            '%s "%s";' % (key, url.replace('\\', '/'))
            for key, urls in commands.items()
            for url in urls
        ]
        # ... and the main SCSS file we want to use
        content.append(f'@import "{path}";')
        with open(source, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(content))
        # Compile SASS file. Allow @import from template dir, UI dir, Bootstrap dir, CWD
        proc = yield gramex.service.threadpool.submit(
            subprocess.run,
            [
                'node',
                sass_bin,
                source,
                target,
                '--style',
                'compressed',
                '--load-path',
                os.path.dirname(path),
                '--load-path',
                ui_dir,
                '--load-path',
                bootstrap_dir,
                '--load-path',
                os.getcwd(),
            ],
            capture_output=True,
            input='\n'.join(content),
            encoding='utf-8',
        )
        if proc.returncode:
            # If there's an error, remove the generated files and raise an error
            os.remove(source)
            raise RuntimeError(f'.sass compilation failure:\n{proc.stderr}\n{proc.stdout}')
    return _sourcemap(handler, target, 'text/css')


@coroutine
def jscompiler(
    handler: gramex.handlers.FileHandler, path: str, target_ext: str, exe: str, cmd: str
) -> bytes:
    '''Compile a file (Vue, TypeScript), etc into a JS file using Node.js

    Examples:
        >>> jscompiler(
        ...     handler, path='x.ts', target_ext='.js', exe='/path/to/tsc',
        ...     cmd='node $exe $filename --outDir $targetDir --sourceMap')

    Parameters:

        handler: the[FileHandler][gramex.handlers.FileHandler] serving this file
        path: absolute path of input file to compile into JavaScript
        target_ext: extension of output file (e.g. `.js`, `.min.js`)
        exe: path to the compiler's JS executable (e.g. `/path/to/tsc`)
        cmd: command line to run. This substitutes 3 variables:
            - `$exe` for the `exe` parameter
            - `$filename` for the absolute path to the input file
            - `$targetDir` for the absolute path to the output directory

    Returns:

        compiled JS file or source map if ?_map is specified
    '''
    # Get valid variables from URL query parameters
    # Create cache key based on state = path. Output to <cache-key>.js
    path = os.path.normpath(path).replace('\\', '/')
    ext = os.path.splitext(path)[-1]
    cache_key = _get_cache_key([path])
    target_dir = _join(cache_dir, f'{ext}-{cache_key}')
    target = os.path.join(target_dir, os.path.basename(path[: -len(ext)] + target_ext))

    # Recompile if output target is missing, or path has been updated
    if not os.path.exists(target) or os.stat(path).st_mtime > os.stat(target).st_mtime:
        cwd, filename = os.path.split(path)
        subs = {'exe': exe, 'filename': filename, 'targetDir': target_dir}
        cmd = [string.Template(x).substitute(subs) for x in cmd.split()]
        app_log.debug(f'Compiling .{ext}: {" ".join(cmd)}')
        proc = yield gramex.service.threadpool.submit(
            subprocess.run, cmd, cwd=cwd, capture_output=True, encoding='utf-8'
        )
        if proc.returncode:
            raise RuntimeError(f'.{ext} compilation failure:\n{proc.stderr}\n{proc.stdout}')

    return _sourcemap(handler, target, 'text/javascript')


ts = partial(
    jscompiler,
    target_ext='.js',
    exe=ts_path,
    cmd='node --unhandled-rejections=strict $exe $filename --outDir $targetDir --sourceMap',
)
vue = partial(
    jscompiler,
    target_ext='.min.js',
    exe=vue_path,
    cmd='node --unhandled-rejections=strict $exe build --target wc $filename --dest $targetDir',
)


def _sourcemap(handler: gramex.handlers.FileHandler, target: str, mime: str) -> bytes:
    '''Returns the compiled target file OR the source map if ?_map is set.

    Examples:
        >>> _sourcemap(handler, 'output.js', 'text/javascript')

    Parameters:

        handler: the [FileHandler][gramex.handlers.FileHandler] serving this file
        target: absolute path of compiled output
        mime: MIME type of compiled output

    Returns:

        source map or target file contents

    This is used by FileHandlers compiling Vue, TS, SASS, etc.

    If the URL has a ?_map, it serves `{target}.map` as a JSON file.
    Else it serves the `{target}` as `mime` type,
    replacing `sourceMappingURL` with the current URL + `?_map`.
    '''
    if '_map' in handler.args:
        # Serve JSON source map if requested
        handler.set_header('Content-Type', 'application/json')
        return gramex.cache.open(target + '.map', 'bin', mode='rb')
    else:
        # Serve compiled file if there's no ?_map
        handler.set_header('Content-Type', mime)
        content = gramex.cache.open(target, 'bin', mode='rb')
        # ... but replace the sourceMappingURL with URL + ?_map
        url = urlparse(handler.request.uri)
        query = parse_qs(url.query, keep_blank_values=True)
        query.setdefault('_map', [''])
        source_map = os.path.basename(url.path) + '?' + urlencode(query, doseq=True)
        return re.sub(
            rb' sourceMappingURL=(\S+)',
            rb' sourceMappingURL=' + source_map.encode('utf-8'),
            content,
        )
