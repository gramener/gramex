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
import six
import sys
import yaml
import string
import logging
import datetime
import dateutil.tz
import dateutil.parser
from pathlib import Path
from copy import deepcopy
from six import string_types
from pydoc import locate as _locate
from yaml import Loader, MappingNode
from json import loads, JSONEncoder, JSONDecoder
from yaml.constructor import ConstructorError
from orderedattrdict import AttrDict, DefaultAttrDict

app_log = logging.getLogger('gramex')
str_utf8 = str('utf-8')             # noqa


def walk(node):
    '''
    Bottom-up recursive walk through a data structure yielding a (key, value,
    node) tuple for every entry.

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
        for key, value in node.items():
            for item in walk(value):
                yield item
            yield key, value, node
    elif isinstance(node, list):
        for index, value in enumerate(node):
            for item in walk(value):
                yield item
            yield index, value, node


def merge(old, new, mode='overwrite'):
    '''
    Update old dict with new dict recursively.

        >>> merge({'a': {'x': 1}}, {'a': {'y': 2}})
        {'a': {'x': 1, 'y': 2}}

    If ``mode='overwrite'``, the old dict is overwritten (default).
    If ``mode='setdefault'``, the old dict values are updated only if missing.
    '''
    for key in new:
        if key in old and hasattr(old[key], 'items') and hasattr(new[key], 'items'):
            merge(old=old[key], new=new[key], mode=mode)
        else:
            if mode == 'overwrite' or key not in old:
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
        '+config returns layers merged in order, removing null keys'
        conf = AttrDict()
        for name, config in self.items():
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


def _setup_variables():
    '''Initialise variables'''
    variables = DefaultAttrDict(str)
    # Load all environment variables
    variables.update(os.environ)

    # Define GRAMEXDATA folder based on the system
    if 'GRAMEXDATA' not in variables:
        if sys.platform.startswith('linux') or sys.platform == 'cygwin':
            variables['GRAMEXDATA'] = os.path.expanduser('~/.config/gramexdata')
        elif sys.platform == 'win32':
            variables['GRAMEXDATA'] = os.path.join(variables['LOCALAPPDATA'], 'Gramex Data')
        elif sys.platform == 'darwin':
            variables['GRAMEXDATA'] = os.path.expanduser(
                '~/Library/Application Support/Gramex Data')
        else:
            variables['GRAMEXDATA'] = os.path.abspath('.')
            app_log.warn('$GRAMEXDATA set to %s for OS %s', variables['GRAMEXDATA'], sys.platform)

    return variables


variables = _setup_variables()


def _substitute_variable(val):
    '''
    If val contains a ${VAR} or $VAR and VAR is in the variables global,
    substitute it.

    Direct variables are substituted as-is. For example, $x will return
    variables['x'] without converting it to a string. Otherwise, treat it as a
    string tempate. So "/$x/" will return "/1/" if x=1.
    '''
    if not isinstance(val, string_types):
        return val
    if val.startswith('$') and val[1:] in variables:
        return variables[val[1:]]
    else:
        try:
            return string.Template(val).substitute(variables)
        except ValueError:
            raise ValueError('Use $$ instead of $ in %s' % val)


def _calc_value(val, key):
    '''
    Calculate the value to assign to this key.

    If ``val`` is not a dictionary that has a ``function`` key, return it as-is.

    If it has a function key, call that function (with specified args, kwargs,
    etc) and allow the ``key`` parameter as an argument.

    If the function is a generator, the first value is used.
    '''
    if hasattr(val, 'get') and val.get('function'):
        from .transforms import build_transform
        function = build_transform(val, vars={'key': None}, filename='config:%s' % key)
        for result in function(key):
            if result is not None:
                return result
        return val.get('default')
    else:
        return _substitute_variable(val)


def _from_yaml(loader, node):
    '''
    Load mapping as AttrDict, preserving order. Raise error on duplicate keys
    '''
    # Based on yaml.constructor.SafeConstructor.construct_mapping()
    attrdict = AttrDict()
    yield attrdict
    if not isinstance(node, MappingNode):
        raise ConstructorError(
            None, None, 'expected a mapping node, but found %s' % node.id, node.start_mark)
    loader.flatten_mapping(node)
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=False)
        try:
            hash(key)
        except TypeError as exc:
            raise ConstructorError(
                'while constructing a mapping', node.start_mark,
                'found unacceptable key (%s)' % exc, key_node.start_mark)
        if key in attrdict:
            raise ConstructorError(
                'while constructing a mapping', node.start_mark,
                'found duplicate key (%s)' % key, key_node.start_mark)
        attrdict[key] = loader.construct_object(value_node, deep=False)


class ConfigYAMLLoader(Loader):
    '''
    A YAML loader that loads a YAML file into an ordered AttrDict. Usage::

        >>> attrdict = yaml.load(yaml_string, Loader=ConfigYAMLLoader)

    If there are duplicate keys, this raises an error.
    '''
    def __init__(self, *args, **kwargs):
        super(ConfigYAMLLoader, self).__init__(*args, **kwargs)
        self.add_constructor(u'tag:yaml.org,2002:map', _from_yaml)
        self.add_constructor(u'tag:yaml.org,2002:omap', _from_yaml)


def _yaml_open(path, default=AttrDict()):
    '''
    Load a YAML path.Path as AttrDict. Replace {VAR} with variables
    '''
    path = path.absolute()
    if not path.exists():
        if path not in _warned_paths:
            app_log.warning('Missing config: %s', path)
            _warned_paths.add(path)
        return default
    app_log.debug('Loading config: %s', path)
    with path.open(encoding='utf-8') as handle:
        result = yaml.load(handle, Loader=ConfigYAMLLoader)
    if result is None:
        app_log.warning('Empty config: %s', path)
        return default

    # Variables based on YAML file location
    yaml_path = str(path.parent)
    yaml_vars = {
        'GRAMEXPATH': _gramex_path,     # Path to Gramex root directory
        'YAMLPATH': yaml_path,          # Path to YAML folder
        'YAMLFILE': str(path),          # Path to YAML file
    }
    try:
        # Relative URL from cwd to YAML folder. However, if the YAML is in a
        # different drive than the current directory, this will fail. In that
        # case ignore it.
        yaml_vars['YAMLURL'] = os.path.relpath(yaml_path).replace(os.path.sep, '/')
    except ValueError:
        pass
    variables.update(yaml_vars)

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

    # Substitute variables
    for key, value, node in walk(result):
        if isinstance(value, string_types):
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
                el[prefix + subkey] = el.pop(subkey)
    return config


def load_imports(config, source):
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
        import:
            something: update*.yaml     # Can be any glob, e.g. */gramex.yaml

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
    '''
    imported_paths = [_pathstat(source)]
    root = source.absolute().parent
    for key, value, node in list(walk(config)):
        if key == 'import':
            for name, conf in value.items():
                if not isinstance(conf, dict):
                    conf = AttrDict(path=conf)
                paths = root.glob(conf.path) if '*' in conf.path else [Path(conf.path)]
                for path in paths:
                    new_conf = _yaml_open(root.joinpath(path))
                    if 'namespace' in conf:
                        prefix = Path(path).as_posix()
                        new_conf = _add_ns(new_conf, conf['namespace'], prefix)
                    imported_paths += load_imports(new_conf, source=path)
                    merge(old=node, new=new_conf, mode='setdefault')
            # Delete the import key
            del node[key]
    return imported_paths


class PathConfig(AttrDict):
    '''
    An ``AttrDict`` that is loaded from a path as a YAML file. For e.g.,
    ``conf = PathConfig(path)`` loads the YAML file at ``path`` as an AttrDict.
    ``+conf`` reloads the path if required.

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
    __info__.imports
        A list of imported files, stored as an ``AttrDict`` with 2 attributes:

        path
            The path that was imported, stored as a ``pathlib.Path``
        stat
            The ``os.stat()`` information about this file (or ``None`` if the
            file is missing.)
    '''
    def __init__(self, path):
        super(PathConfig, self).__init__()
        self.__info__ = AttrDict(path=Path(path), imports=[])
        self.__pos__()

    def __pos__(self):
        '''+config reloads this config (if it has a path)'''
        path = self.__info__.path

        # We must reload the layer if nothing has been imported...
        reload = not self.__info__.imports
        # ... or if an imported file is deleted / updated
        for imp in self.__info__.imports:
            exists = imp.path.exists()
            if not exists and imp.stat is not None:
                reload = True
                app_log.info('No config found: %s', imp.path)
                break
            if exists and (imp.path.stat().st_mtime > imp.stat.st_mtime or
                           imp.path.stat().st_size != imp.stat.st_size):
                reload = True
                app_log.info('Updated config: %s', imp.path)
                break
        if reload:
            self.clear()
            self.update(_yaml_open(path))
            self.__info__.imports = load_imports(self, source=path)
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
    '''
    for module_name in modules:
        module = _locate(module_name, forceload)
        if hasattr(module, path):
            return getattr(module, path)
    return _locate(path, forceload)


_checked_old_certs = []


class CustomJSONEncoder(JSONEncoder):
    '''
    Encodes object to JSON, additionally converting datetime into ISO 8601 format
    '''
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            # Slow but reliable. Handles conversion of numpy objects, mixed types, etc.
            return loads(obj.to_json(orient='records', date_format='iso'))
        if isinstance(obj, datetime.datetime):
            # Use local timezone if no timezone is specified
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=dateutil.tz.tzlocal())
            return obj.isoformat()
        return super(CustomJSONEncoder, self).default(obj)


class CustomJSONDecoder(JSONDecoder):
    '''
    Decodes JSON string, converting ISO 8601 datetime to datetime
    '''
    # Check if a string might be a datetime. Handles variants like:
    # 2001-02-03T04:05:06Z
    # 2001-02-03T04:05:06+000
    # 2001-02-03T04:05:06.000+0000
    re_datetimeval = re.compile('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    re_datetimestr = re.compile('"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

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
            if isinstance(val, six.string_types) and self.re_datetimeval.match(val):
                obj[index] = (key, dateutil.parser.parse(val))
        if callable(self.old_object_pairs_hook):
            return self.old_object_pairs_hook(obj)
        return dict(obj)


def check_old_certs():
    '''
    The latest SSL certificates from certifi don't work for Google Auth. Do
    a one-time check to access accounts.google.com. If it throws an SSL
    error, switch to old SSL certificates. See
    https://github.com/tornadoweb/tornado/issues/1534
    '''
    if not _checked_old_certs:
        _checked_old_certs.append(True)

        import ssl
        from tornado.httpclient import HTTPClient, AsyncHTTPClient

        # Use HTTPClient to check instead of AsyncHTTPClient because it's synchronous.
        _client = HTTPClient()
        try:
            # Use accounts.google.com because we know it fails with new certifi certificates
            # cdn.redhat.com is another site that fails.
            _client.fetch("https://accounts.google.com/")
        except ssl.SSLError:
            try:
                import certifi      # noqa: late import to minimise dependencies
                AsyncHTTPClient.configure(None, defaults=dict(ca_certs=certifi.old_where()))
                app_log.warn('Using old SSL certificates for compatibility')
            except ImportError:
                pass
            try:
                _client.fetch("https://accounts.google.com/")
            except ssl.SSLError:
                app_log.error('Gramex cannot connect to HTTPS sites. Auth may fail')
        except Exception:
            # Ignore any other kind of exception
            app_log.warn('Gramex has no direct Internet connection')
        _client.close()


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
