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
import sys
import yaml
import string
import logging
from pathlib import Path
from copy import deepcopy
from six import string_types
from pydoc import locate as _locate
from orderedattrdict import AttrDict, DefaultAttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader


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
        if sys.platform == 'linux2' or sys.platform == 'cygwin':
            variables['GRAMEXDATA'] = os.path.expanduser('~/.config/gramexdata')
        elif sys.platform == 'win32':
            variables['GRAMEXDATA'] = os.path.join(variables['LOCALAPPDATA'], 'Gramex Data')
        elif sys.platform == 'darwin':
            variables['GRAMEXDATA'] = os.path.expanduser('~/Library/Application Support/Gramex Data')
        else:
            variables['GRAMEXDATA'] = os.path.abspath('.')
            logging.warn('$GRAMEXDATA set to %s for OS %s', variables['GRAMEXDATA'], sys.platform)

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
        return string.Template(val).substitute(variables)


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
        function = build_transform(val, vars={'key': None}, filename='config>%s' % key)
        for result in function(key):
            return result
    else:
        return _substitute_variable(val)


def _yaml_open(path, default=AttrDict()):
    'Load a YAML path.Path as AttrDict. Replace {VAR} with variables'
    path = path.absolute()
    if not path.exists():
        if path not in _warned_paths:
            logging.warning('Missing config: %s', path)
            _warned_paths.add(path)
        return default
    logging.debug('Loading config: %s', path)
    with path.open(encoding='utf-8') as handle:
        result = yaml.load(handle, Loader=AttrDictYAMLLoader)
    if result is None:
        logging.warning('Empty config: %s', path)
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
            something: update.yaml

    ... and ``update.yaml`` looks like this::

        app:
            port: 30
            new: yes

    ... then after this function is called, ``config`` looks like this::

        app:
            port: 30        # Updated by update.yaml
            start: true     # From base.yaml
            new: yes        # From update.yaml
        path: /             # From base.yaml

    The ``import:`` keys are deleted. The return value contains :func:_pathstat
    values for ``base.yaml`` and ``update.yaml`` in that order.
    '''
    imported_paths = [_pathstat(source)]
    root = source.absolute().parent
    for key, value, node in list(walk(config)):
        if key == 'import':
            for name, pattern in value.items():
                paths = root.glob(pattern) if '*' in pattern else [Path(pattern)]
                for path in paths:
                    new_conf = _yaml_open(root.joinpath(path))
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
        '+config reloads this config (if it has a path)'
        path = self.__info__.path

        # We must reload the layer if nothing has been imported...
        reload = not self.__info__.imports
        # ... or if an imported file is deleted / updated
        for imp in self.__info__.imports:
            exists = imp.path.exists()
            if not exists and imp.stat is not None:
                reload = True
                logging.info('No config found: %s', imp.path)
                break
            if exists and (imp.path.stat().st_mtime > imp.stat.st_mtime or
                           imp.path.stat().st_size != imp.stat.st_size):
                reload = True
                logging.info('Updated config: %s', imp.path)
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

    ``names`` is a mapping of pre-defined names to objects. So ``locate('x',
    names={'x': str})`` will return ``str``.

    ``modules`` is a list of modules to search for the path in first. So
    ``locate('FileHandler', modules=[gramex.handlers])`` will return
    ``gramex.handlers.FileHandler``.
    '''
    for module_name in modules:
        module = _locate(module_name, forceload)
        if hasattr(module, path):
            return getattr(module, path)
    return _locate(path, forceload)
