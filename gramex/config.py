'''
Manages YAML config files as layered configurations with imports.

:class:PathConfig loads YAML files from a path::

    pc = PathConfig('/path/to/file.yaml')

This can be reloaded via the ``+`` operator. ``+pc`` reloads the YAML file
(but only if it is newer than before.)

:class:ChainConfig chains multiple YAML files into a single config. For example
this merges ``base.yaml`` and ``next.yaml`` in sequence::

    cc = ChainConfig()
    cc['base'] = PathConfig('base.yaml')
    cc['next'] = PathConfig('next.yaml')

To get the merged file, use ``+cc``. This updates the PathConfig files and
merges the YAMLs.
'''

import os
import re
import csv
import sys
import yaml
import string
import socket
import inspect
import logging
import datetime
import dateutil.tz
import dateutil.parser
from pathlib import Path
from copy import deepcopy
from random import choice
from fnmatch import fnmatch
from collections import OrderedDict
from pydoc import locate as _locate, ErrorDuringImport
from yaml import SafeLoader, MappingNode
from json import loads, JSONEncoder, JSONDecoder
from yaml.constructor import ConstructorError
from orderedattrdict import AttrDict, DefaultAttrDict
from slugify import slugify
from errno import EACCES, EPERM

# We don't use six -- but import into globals() for _yaml_open().
# This allows YAML conditionals like `key if six.text_type(...): val`
import six  # noqa


ERROR_SHARING_VIOLATION = 32  # from winerror.ERROR_SHARING_VIOLATION

# gramex.config.app_log is the default logger used by all of gramex
# If it's not there, create one.
logging.basicConfig()
app_log = logging.getLogger('gramex')

# app_log_extra has additional parameters that may be used by the logger
app_log_extra = {'port': 'PORT'}
app_log = logging.LoggerAdapter(app_log, app_log_extra)

# Common slug patterns
slug = AttrDict(
    # Python modules must be lowercase, with letters, numbers or _, separated by _
    module=lambda s: slugify(s, lowercase=True, regex_pattern=r'[^a-z0-9_]+', separator='_'),
    # Allow files to contain ASCII characters except
    #   - spaces
    #   - wildcards: * or ?
    #   - quotes: " or '
    #   - directory or drive separators: / or \ or :
    #   - pipe symbol: |
    filename=lambda s: slugify(s, regex_pattern=r'[^!#$%&()+,-.0-9;<=>@A-Z\[\]^_`a-z{}~]'),
)


def walk(node):
    '''
    Bottom-up recursive walk through a data structure yielding a (key, value,
    node) tuple for every entry. ``node[key] == value`` is true in every entry.

    For example::

        >>> list(walk([{'x': 1}]))
        [
            ('x', 1, {'x': 1}),         # leaf:   key, value, node
            (0, {'x': 1}, [{'x': 1}])   # parent: index, value, node
        ]

    Circular linkage can lead to a RuntimeError::

        >>> x = {}
        >>> x['x'] = x
        >>> list(walk(x))
        ...
        RuntimeError: maximum recursion depth exceeded
    '''
    if hasattr(node, 'items'):
        # Convert note.items() to list to prevent keys changing during iteration
        for key, value in list(node.items()):
            yield from walk(value)
            yield key, value, node
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value)
            yield index, value, node


def merge(old, new, mode='overwrite', warn=None, _path=''):
    '''
    Update old dict with new dict recursively.

        >>> merge({'a': {'x': 1}}, {'a': {'y': 2}})
        {'a': {'x': 1, 'y': 2}}

    If ``new`` is a list, convert into a dict with random keys.

    If ``mode='overwrite'``, the old dict is overwritten (default).
    If ``mode='setdefault'``, the old dict values are updated only if missing.

    ``warn=`` is an optional list of key paths. Any conflict on dictionaries
    matching any of these paths is logged as a warning. For example,
    ``warn=['url.*', 'watch.*']`` warns if any url: sub-key or watch: sub-key
    has a conflict.
    '''
    for key in new:
        if key in old and hasattr(old[key], 'items') and hasattr(new[key], 'items'):
            path_key = _path + ('.' if _path else '') + str(key)
            if warn is not None:
                for pattern in warn:
                    if fnmatch(path_key, pattern):
                        app_log.warning(f'Duplicate key: {path_key}')
                        break
            merge(old=old[key], new=new[key], mode=mode, warn=warn, _path=path_key)
        elif mode == 'overwrite' or key not in old:
            old[key] = deepcopy(new[key])
    return old


class ChainConfig(AttrDict):
    '''
    An AttrDict that manages multiple configurations as layers.

        >>> config = ChainConfig([
        ...     ('base', PathConfig('gramex.yaml')),
        ...     ('app1', PathConfig('app.yaml')),
        ...     ('app2', AttrDict())
        ... ])

    Any dict-compatible values are allowed. ``+config`` returns the merged values.
    '''

    def __pos__(self):
        '''+config returns layers merged in order, removing null keys'''
        conf = AttrDict()
        for _name, config in self.items():
            if hasattr(config, '__pos__'):
                config.__pos__()
            merge(old=conf, new=config, mode='overwrite')

        # Remove keys where the value is None
        for key, value, node in list(walk(conf)):
            if value is None:
                del node[key]

        return conf


# Paths that users have already been warned about. Don't warn them again
_warned_paths = set()
# Get the directory where gramex is located. This is the same as the directory
# where this file (config.py) is located.
_gramex_path = os.path.dirname(os.path.abspath(__file__))
# Secret variables
secrets = {}


def setup_variables():
    '''Initialise variables'''
    variables = DefaultAttrDict(str)
    # Load all environment variables, and overwrite with secrets
    variables.update(os.environ)
    variables.update(secrets)
    # GRAMEXPATH is the Gramex root directory
    variables['GRAMEXPATH'] = _gramex_path
    # GRAMEXAPPS is the Gramex apps directory
    variables['GRAMEXAPPS'] = os.path.join(_gramex_path, 'apps')
    # GRAMEXHOST is the hostname
    variables['GRAMEXHOST'] = socket.gethostname()
    # GRAMEXDATA varies based on OS
    if 'GRAMEXDATA' not in variables:
        if sys.platform.startswith('linux') or sys.platform == 'cygwin':
            variables['GRAMEXDATA'] = os.path.expanduser('~/.config/gramexdata')
        elif sys.platform == 'win32':
            variables['GRAMEXDATA'] = os.path.join(variables['LOCALAPPDATA'], 'Gramex Data')
        elif sys.platform == 'darwin':
            variables['GRAMEXDATA'] = os.path.expanduser(
                '~/Library/Application Support/Gramex Data'
            )
        else:
            variables['GRAMEXDATA'] = os.path.abspath('.')
            app_log.warning(f'$GRAMEXDATA set to {variables["GRAMEXDATA"]} for OS {sys.platform}')

    return variables


variables = setup_variables()


def _substitute_variable(val):
    '''
    If val contains a ${VAR} or $VAR and VAR is in the variables global,
    substitute it.

    Direct variables are substituted as-is. For example, $x will return
    variables['x'] without converting it to a string. Otherwise, treat it as a
    string tempate. So "/$x/" will return "/1/" if x=1.
    '''
    if not isinstance(val, str):
        return val
    if val.startswith('$') and val[1:] in variables:
        return variables[val[1:]]
    else:
        try:
            return string.Template(val).substitute(variables)
        except ValueError:
            raise ValueError(f'Use $$ instead of $ in {val}')


def _calc_value(val, key):
    '''Calculate the value to assign to this key.

    If val is a scalar (string, boolean, dict, etc), return as-is.

    If it's a list or a dict, return calculated values of underlying values.

    If it's a dict with a `function` key, evaluation the function and return the non-None value.
    If the returned value(s) are None, return the calculated 'default' value.
    '''
    if isinstance(val, dict):
        if val.get('function'):
            from .transforms import build_transform

            function = build_transform(val, vars={'key': None}, filename=f'config:{key}')
            try:
                for result in function(key):
                    if result is not None:
                        return result
            except Exception:
                app_log.exception(f'Error in calculated variable: {key}: {val}')
            return _calc_value(val.get('default', None), key)
        else:
            return {k: _calc_value(v, k) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [_calc_value(v, key) for v in val]
    else:
        return _substitute_variable(val)


_valid_key_chars = string.ascii_letters + string.digits


def random_string(size, chars=_valid_key_chars):
    '''Return random string of length size using chars (which defaults to alphanumeric)'''
    # B311:random random() is safe since it's for non-cryptographic use
    return ''.join(choice(chars) for index in range(size))  # nosec B311


RANDOM_KEY = r'$*'


def _from_yaml(loader, node):
    '''
    Load mapping as AttrDict, preserving order. Raise error on duplicate keys
    '''
    # Based on yaml.constructor.SafeConstructor.construct_mapping()
    attrdict = AttrDict()
    yield attrdict
    if not isinstance(node, MappingNode):
        raise ConstructorError(
            None, None, f'expected a mapping node, but found {node.id}', node.start_mark
        )
    loader.flatten_mapping(node)
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=False)
        if isinstance(key, str) and RANDOM_KEY in key:
            # With k=5 there's a <0.1% chance of collision even for 1mn uses.
            # (1 - decimal.Decimal(62 ** -5)) ** 1000000 ~ 0.999
            key = key.replace(RANDOM_KEY, random_string(5))
        try:
            hash(key)
        except TypeError as exc:
            raise ConstructorError(
                'while constructing a mapping',
                node.start_mark,
                f'found unacceptable key ({exc})',
                key_node.start_mark,
            )
        if key in attrdict:
            raise ConstructorError(
                'while constructing a mapping',
                node.start_mark,
                f'found duplicate key ({key})',
                key_node.start_mark,
            )
        attrdict[key] = loader.construct_object(value_node, deep=False)


class ConfigYAMLLoader(SafeLoader):
    '''
    A YAML loader that loads a YAML file into an ordered AttrDict. Usage::

        >>> attrdict = yaml.load(yaml_string, Loader=ConfigYAMLLoader)

    If there are duplicate keys, this raises an error.
    '''

    def __init__(self, *args, **kwargs):
        super(ConfigYAMLLoader, self).__init__(*args, **kwargs)
        self.add_constructor('tag:yaml.org,2002:map', _from_yaml)
        self.add_constructor('tag:yaml.org,2002:omap', _from_yaml)


def _yaml_open(path, default=AttrDict(), **kwargs):
    '''
    Load a YAML path.Path as AttrDict. Replace ${VAR} or $VAR with variables.
    Defines special variables $YAMLPATH as the absolute path of the YAML file,
    and $YAMLURL as the path relative to current directory. These can be
    overridden via keyward arguments (e.g. ``YAMLURL=...``)

    If key has " if ", include it only if the condition (eval-ed in Python) is
    true.

    If the path is missing, or YAML has a parse error, or the YAML is not a
    dict, returns the default value.
    '''
    path = path.absolute()
    if not path.exists():
        if path not in _warned_paths:
            app_log.warning(f'Missing config: {path}')
            _warned_paths.add(path)
        return default
    app_log.debug(f'Loading config: {path}')
    with path.open(encoding='utf-8') as handle:
        try:
            # B506:yaml_load we use a safe loader
            result = yaml.load(handle, Loader=ConfigYAMLLoader)  # nosec B506
        except Exception:
            app_log.exception(f'Config error: {path}')
            return default
    if not isinstance(result, AttrDict):
        if result is not None:
            app_log.warning(f'Config is not a dict: {path}')
        return default

    # Variables based on YAML file location
    yaml_path = str(path.parent)
    kwargs.setdefault('YAMLPATH', yaml_path)  # Path to YAML folder
    kwargs.setdefault('YAMLFILE', str(path))  # Path to YAML file
    # $YAMLURL defaults to the relative URL from cwd to YAML folder.
    try:
        yamlurl = os.path.relpath(yaml_path)
    except ValueError:
        # If YAML is in a different drive, this fails. So don't set YAMLURL.
        # Impact: $YAMLURL is undefined for imports from a different drive.
        pass
    else:
        kwargs.setdefault('YAMLURL', yamlurl)
    # Typically, we use /$YAMLURL/url - so strip the slashes. Replace backslashes
    if isinstance(kwargs.get('YAMLURL'), str):
        kwargs['YAMLURL'] = kwargs['YAMLURL'].replace('\\', '/').strip('/')
    variables.update(kwargs)

    # Update context with the variables section.
    # key: value                     sets key = value
    # key: {function: fn}            sets key = fn(key)
    # key: {default: value}          sets key = value if it's not already set
    # key: {default: {function: fn}} sets key = fn(key) if it's not already set
    if 'variables' in result:
        for key, val in result['variables'].items():
            if hasattr(val, 'get') and 'default' in val and 'function' not in val:
                variables.setdefault(key, _calc_value(val['default'], key))
            else:
                variables[key] = _calc_value(val, key)
        del result['variables']

    # Evaluate conditionals. "x if cond: y" becomes "x: y" if cond evals to True
    remove, replace = [], []
    frozen_vars = dict(variables)
    for key, _value, node in walk(result):
        if isinstance(key, str) and ' if ' in key:
            # Evaluate conditional
            base, expr = key.split(' if ', 2)
            try:
                # B307:eval this is safe since `expr` is written by app developer
                condition = eval(expr, globals(), frozen_vars)  # nosec B307
            except Exception:
                condition = False
                app_log.exception(f'Failed condition evaluation: {key}')
            if condition:
                replace.append((node, key, base))
            else:
                remove.append((node, key))
    for node, key in remove:
        del node[key]
    for node, key, base in replace:
        node[base] = node.pop(key)

    # Substitute variables
    for key, value, node in walk(result):
        if isinstance(value, str):
            # Backward compatibility: before v1.0.4, we used {.} for {YAMLPATH}
            value = value.replace('{.}', '$YAMLPATH')
            # Substitute with variables in context, defaulting to ''
            node[key] = _substitute_variable(value)
    return result


def _pathstat(path):
    '''
    Return a path stat object, which has 2 attributes/keys: ``.path`` is the
    same as the ``path`` parameter. ``stat`` is the result of ``os.stat``. If
    path is missing, ``stat`` has ``st_mtime`` and ``st_size`` set to ``0``.
    '''
    # If path doesn't exist, create a dummy stat structure with
    # safe defaults (old mtime, 0 filesize, etc)
    stat = path.stat() if path.exists() else AttrDict(st_mtime=0, st_size=0)
    return AttrDict(path=path, stat=stat)


def _add_ns(config, namespace, prefix):
    '''
    Given a YAML config (basically a dict), add prefix to specified namespaces.

    For example::

        >>> _add_ns({'x': 1}, '*', 'a')
        {'a.x': 1}
        >>> _add_ns({'x': {'y': 1}}, ['*', 'x'], 'a')
        {'a.x': {'a.y': 1}}
    '''
    if not isinstance(namespace, list):
        namespace = [namespace]
    # Sort in descending order of key depth. So "x.y" is before "x" is before "*"
    namespace = sorted(namespace, key=lambda ns: -1 if ns == '*' else ns.count('.'), reverse=True)
    prefix += ':'
    for keypath in namespace:
        if keypath == '*':
            el = config
        else:
            el = objectpath(config, keypath, default={})
        if isinstance(el, dict):
            for subkey in list(el.keys()):
                if subkey not in {'import'}:
                    el[prefix + subkey] = el.pop(subkey)
    return config


def load_imports(config, source, warn=None):
    '''
    Post-process a config for imports.

    ``config`` is the data to process. ``source`` is the path where it was
    loaded from.

    If ``config`` has an ``import:`` key, treat all values below that as YAML
    files (specified relative to ``source``) and import them in sequence.

    Return a list of imported paths as :func:_pathstat objects. (This includes
    ``source``.)

    For example, if the ``source`` is  ``base.yaml`` (which has the below
    configuration) and is loaded into ``config``::

        app:
            port: 20
            start: true
        path: /
        import: update*.yaml    # Can be any glob, e.g. */gramex.yaml

    ... and ``update.yaml`` looks like this::

        app:
            port: 30
            new: yes

    ... then after this function is called, ``config`` looks like this::

        app:
            port: 20        # From base.yaml. NOT updated by update.yaml
            start: true     # From base.yaml
            new: yes        # From update.yaml
        path: /             # From base.yaml

    The ``import:`` keys are deleted. The return value contains :func:_pathstat
    values for ``base.yaml`` and ``update.yaml`` in that order.

    Multiple ``import:`` values can be specified as a dictionary::

        import:
            first-app: app1/*.yaml
            next-app: app2/*.yaml

    To import sub-keys as namespaces, use::

        import:
            app: {path: */gramex.yaml, namespace: 'url'}

    This prefixes all keys under ``url:``. Here are more examples::

        namespace: True             # Add namespace to all top-level keys
        namespace: url              # Add namespace to url.*
        namespace: log.loggers      # Add namespace to log.loggers.*
        namespace: [True, url]      # Add namespace to top level keys and url.*

    By default, the prefix is the relative path of the imported YAML file
    (relative to the importer).

    ``warn=`` is an optional list of key paths. Any conflict on dictionaries
    matching any of these paths is logged as a warning. For example,
    ``warn=['url.*', 'watch.*']`` warns if any url: sub-key or watch: sub-key
    has a conflict.
    '''
    imported_paths = [_pathstat(source)]
    root = source.absolute().parent
    for key, value, node in list(walk(config)):
        if isinstance(key, str) and key.startswith('import.merge'):
            # Strip the top level key(s) from import.merge values
            if isinstance(value, dict):
                for name, conf in value.items():
                    node[name] = conf
            elif value:
                raise ValueError(f'import.merge: must be dict, not {value!r} at {source}')
            # Delete the import key
            del node[key]
        elif key == 'import':
            # Convert "import: path" to "import: {app: path}"
            if isinstance(value, str):
                value = {'apps': value}
            # Allow "import: [path, path]" to "import: {app0: path, app1: path}"
            elif isinstance(value, list):
                value = OrderedDict(((f'app{i}', conf) for i, conf in enumerate(value)))
            # By now, import: should be a dict
            elif not isinstance(value, dict):
                raise ValueError(f'import: must be string/list/dict, not {value!r} at {source}')
            # If already a dict with a single import via 'path', convert to dict of apps
            if 'path' in value:
                value = {'app': value}
            for name, conf in value.items():
                if not isinstance(conf, dict):
                    conf = AttrDict(path=conf)
                if 'path' not in conf:
                    raise ValueError(f'import: has no conf at {source}')
                paths = conf.pop('path')
                paths = paths if isinstance(paths, list) else [paths]
                globbed_paths = []
                for path in paths:
                    globbed_paths += sorted(root.glob(path)) if '*' in path else [Path(path)]
                ns = conf.pop('namespace', None)
                for path in globbed_paths:
                    abspath = root.joinpath(path)
                    new_conf = _yaml_open(abspath, **conf)
                    if ns is not None:
                        prefix = Path(path).as_posix()
                        new_conf = _add_ns(new_conf, ns, name + ':' + prefix)
                    imported_paths += load_imports(new_conf, source=abspath)
                    merge(old=node, new=new_conf, mode='setdefault', warn=warn)
            # Delete the import key
            del node[key]
    return imported_paths


class PathConfig(AttrDict):
    '''
    An ``AttrDict`` that is loaded from a path as a YAML file. For e.g.,
    ``conf = PathConfig(path)`` loads the YAML file at ``path`` as an AttrDict.
    ``+conf`` reloads the path if required.

    ``warn=`` is an optional list of key paths. Any conflict on dictionaries
    matching any of these paths is logged as a warning. For example,
    ``warn=['url.*', 'watch.*']`` warns if any url: sub-key or watch: sub-key
    has a conflict.

    Like http://configure.readthedocs.org/ but supports imports not inheritance.
    This lets us import YAML files in the middle of a YAML structure::

        key:
            import:
                conf1: file1.yaml       # Import file1.yaml here
                conf2: file2.yaml       # Import file2.yaml here

    Each ``PathConfig`` object has an ``__info__`` attribute with the following
    keys:

    __info__.path
        The path that this instance syncs with, stored as a ``pathlib.Path``
    __info__.warn
        The keys to warn in case about in case of an import merge conflict
    __info__.imports
        A list of imported files, stored as an ``AttrDict`` with 2 attributes:

        path
            The path that was imported, stored as a ``pathlib.Path``
        stat
            The ``os.stat()`` information about this file (or ``None`` if the
            file is missing.)
    '''

    duplicate_warn = None

    def __init__(self, path, warn=None):
        super(PathConfig, self).__init__()
        if warn is None:
            warn = self.duplicate_warn
        self.__info__ = AttrDict(path=Path(path), imports=[], warn=warn)
        self.__pos__()

    def __pos__(self):
        '''+config reloads this config (if it has a path)'''
        path = self.__info__.path

        # We must reload the layer if nothing has been imported...
        reload = not self.__info__.imports
        # ... or if an imported file is deleted / updated
        for imp in self.__info__.imports:
            exists = imp.path.exists()
            # If the path existed but has now been deleted, log it
            if not exists and imp.stat is not None:
                reload = True
                app_log.debug(f'Config deleted: {imp.path}')
                break
            if exists and (
                imp.path.stat().st_mtime > imp.stat.st_mtime
                or imp.path.stat().st_size != imp.stat.st_size
            ):
                reload = True
                app_log.info(f'Updated config: {imp.path}')
                break
        if reload:
            self.clear()
            self.update(_yaml_open(path))
            self.__info__.imports = load_imports(self, source=path, warn=self.__info__.warn)
        return self


def locate(path, modules=[], forceload=0):
    '''
    Locate an object by name or dotted path.

    For example, ``locate('str')`` returns the ``str`` built-in.
    ``locate('gramex.handlers.FileHandler')`` returns the class
    ``gramex.handlers.FileHandler``.

    ``modules`` is a list of modules to search for the path in first. So
    ``locate('FileHandler', modules=[gramex.handlers])`` will return
    ``gramex.handlers.FileHandler``.

    If importing raises an Exception, log it and return None.
    '''
    try:
        for module_name in modules:
            module = _locate(module_name, forceload)
            if hasattr(module, path):
                return getattr(module, path)
        return _locate(path, forceload)
    except ErrorDuringImport:
        app_log.exception(f'Exception when importing {path}')
        return None


class CustomJSONEncoder(JSONEncoder):
    '''
    Encodes object to JSON, additionally converting datetime into ISO 8601 format
    '''

    def default(self, obj):
        import numpy as np

        if hasattr(obj, 'to_dict'):
            # Slow but reliable. Handles conversion of numpy objects, mixed types, etc.
            return loads(
                obj.to_json(orient='records', date_format='iso'), object_pairs_hook=OrderedDict
            )
        elif isinstance(obj, datetime.datetime):
            # Use local timezone if no timezone is specified
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=dateutil.tz.tzlocal())
            return obj.isoformat()
        elif isinstance(obj, np.datetime64):
            obj = obj.item()
            if isinstance(obj, datetime.datetime) and obj.tzinfo is None:
                obj = obj.replace(tzinfo=dateutil.tz.tzlocal())
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.bytes_):
            return obj.decode('utf-8')
        return super(CustomJSONEncoder, self).default(obj)


class CustomJSONDecoder(JSONDecoder):
    '''
    Decodes JSON string, converting ISO 8601 datetime to datetime
    '''

    # Check if a string might be a datetime. Handles variants like:
    # 2001-02-03T04:05:06Z
    # 2001-02-03T04:05:06+000
    # 2001-02-03T04:05:06.000+0000
    re_datetimeval = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    re_datetimestr = re.compile(r'"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

    def __init__(self, *args, **kwargs):
        self.old_object_pairs_hook = kwargs.get('object_pairs_hook')
        kwargs['object_pairs_hook'] = self.convert
        super(CustomJSONDecoder, self).__init__(*args, **kwargs)

    def decode(self, obj):
        if self.re_datetimestr.match(obj):
            return dateutil.parser.parse(obj[1:-1])
        return super(CustomJSONDecoder, self).decode(obj)

    def convert(self, obj):
        for index, (key, val) in enumerate(obj):
            if isinstance(val, str) and self.re_datetimeval.match(val):
                obj[index] = (key, dateutil.parser.parse(val))
        if callable(self.old_object_pairs_hook):
            return self.old_object_pairs_hook(obj)
        return dict(obj)


def objectpath(node, keypath, default=None):
    '''
    Traverse down a dot-separated object path into dict items or object attrs.
    For example, ``objectpath(handler, 'request.headers.User-Agent')`` returns
    ``handler.request.headers['User-Agent']``. Dictionary access is preferred.
    Returns ``None`` if the path is not found.
    '''
    for key in keypath.split('.'):
        if hasattr(node, '__getitem__'):
            node = node.get(key)
        else:
            node = getattr(node, key, None)
        if node is None:
            return default
    return node


def recursive_encode(data, encoding='utf-8'):
    '''
    Convert all Unicode values into UTF-8 encoded byte strings in-place
    '''
    for key, value, node in walk(data):
        if isinstance(key, str):
            newkey = key.encode(encoding)
            node[newkey] = node.pop(key)
            key = newkey
        if isinstance(value, str):
            node[key] = value.encode(encoding)


def prune_keys(conf, keys={}):
    '''
    Returns a deep copy of a configuration removing specified keys.
    ``prune_keys(conf, {'comment'})`` drops the "comment" key from any dict or sub-dict.
    '''
    if isinstance(conf, dict):
        conf = AttrDict({k: prune_keys(v, keys) for k, v in conf.items() if k not in keys})
    elif isinstance(conf, (list, tuple)):
        conf = [prune_keys(v, keys) for v in conf]
    return conf


class TimedRotatingCSVHandler(logging.handlers.TimedRotatingFileHandler):
    '''
    Same as logging.handlers.TimedRotatingFileHandler, but writes to a CSV.
    The constructor accepts an additional ``keys`` list as input that has
    column keys. When ``.emit()`` is called, it expects an object with the
    same keys as ``keys``.
    '''

    def __init__(self, *args, **kwargs):
        self.keys = kwargs.pop('keys')
        super(TimedRotatingCSVHandler, self).__init__(*args, **kwargs)

    def _open(self):
        stream = super(TimedRotatingCSVHandler, self)._open()
        self.writer = csv.DictWriter(stream, fieldnames=self.keys, lineterminator='\n')
        return stream

    def emit(self, record):
        try:
            # From logging.handlers.BaseRotatingHandler
            if self.shouldRollover(record):
                self.doRollover()
            # From logging.handlers.StreamHandler
            if self.stream is None:
                self.stream = self._open()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            # On Windows, multiple processes cannot rotate the same file.
            # Ignore this, and just re-open the stream.
            # On Linux, this needs to be tested.
            if e.errno == EPERM or e.errno == EACCES:
                if getattr(e, 'winerror', None) == ERROR_SHARING_VIOLATION:
                    self.stream = self._open()
            else:
                return self.handleError(record)
        try:
            # Write the CSV record instead of the formatted record
            self.writer.writerow(record.msg)
            self.stream.flush()
        except Exception:
            self.handleError(record)


def ioloop_running(loop):
    '''Returns whether the Tornado ioloop is running on not'''
    # TODO: Pressing Ctrl+C may cause this to raise an exception. Explore how to handle that
    return loop.asyncio_loop.is_running()


def used_kwargs(method, kwargs, ignore_keywords=False):
    '''
    Splits kwargs into those used by method, and those that are not.

    Returns a tuple of (used, rest). *used* is a dict subset of kwargs with only
    keys used by method. *rest* has the remaining kwargs keys.

    If the method uses ``**kwargs`` (keywords), it uses all keys. To ignore this
    and return only named arguments, use ``ignore_keywords=True``.
    '''
    # In Pandas 1.5, DataFrame.to_csv and DataFrame.to_excel are wrapped with @deprecate_kwargs.
    # We dive deeper to detect the actual keywords. __wrapped__ is provided by functools.wraps
    # https://docs.python.org/3/library/functools.html
    while hasattr(method, '__wrapped__'):
        method = method.__wrapped__
    argspec = inspect.getfullargspec(method)
    # If method uses **kwargs, return all kwargs (unless you ignore **kwargs)
    if argspec.varkw and not ignore_keywords:
        used, rest = kwargs, {}
    else:
        # Split kwargs into 2 dicts -- used and rest
        used, rest = {}, {}
        for key, val in kwargs.items():
            target = used if key in set(argspec.args) else rest
            target[key] = val
    return used, rest


def setup_secrets(path, max_age_days=1000000, clear=True):
    '''
    Load ``<path>`` (which must be Path) as a YAML file. Update it into gramex.config.variables.

    If there's a ``SECRETS_URL:`` and ``SECRETS_KEY:`` key, the text from ``SECRETS_URL:`` is
    decrypted using ``secrets_key``.

    If there's a ``SECRETS_IMPORT:`` string, list or dict, the values are treated as file patterns
    pointing to other secrets file to be imported.
    '''
    if not path.is_file():
        return

    with path.open(encoding='utf-8') as handle:
        result = yaml.safe_load(handle)
    # Ignore empty .secrets.yaml
    if not result:
        return
    # If it's non-empty, it must be a dict
    if not isinstance(result, dict):
        raise ValueError(f'{path}: must be a YAML file with a single dict')
    # Clear secrets if we are re-initializing. Not if we're importing recursively.
    if clear:
        secrets.clear()
    # If SECRETS_URL: and SECRETS_KEY: are set, fetch secrets from URL and decrypted with the key.
    # This allows changing secrets remotely without access to the server.
    secrets_url = result.pop('SECRETS_URL', None)
    secrets_key = result.pop('SECRETS_KEY', None)
    if secrets_url and secrets_key:
        from urllib.request import urlopen
        from tornado.web import decode_signed_value

        app_log.info(f'Fetching remote secrets from {secrets_url}')
        # Load string from the URL -- but ignore comments. file:// URLs are fine too
        # B310:urllib_urlopen secrets can be local files or URLs
        value = yaml.safe_load(urlopen(secrets_url))  # nosec B310
        value = decode_signed_value(secrets_key, '', value, max_age_days=max_age_days)
        result.update(loads(value.decode('utf-8')))
    # If SECRETS_IMPORT: is set, fetch secrets from those file(s) as well.
    # SECRETS_IMPORT: can be a file pattern, or a list/dict of file patterns
    secrets_import = result.pop('SECRETS_IMPORT', None)
    if secrets_import:
        # Create a list of file patterns to import from
        imports = (
            list(secrets_import.values())
            if isinstance(secrets_import, dict)
            else secrets_import
            if isinstance(secrets_import, (list, tuple))
            else [secrets_import]
        )
        for pattern in imports:
            for import_path in path.parent.glob(pattern):
                setup_secrets(import_path, max_age_days, clear=False)
    secrets.update(result)
