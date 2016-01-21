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

import yaml
import logging
from pathlib import Path
from copy import deepcopy
from six import string_types
from orderedattrdict import AttrDict
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


def merge(old, new, overwrite=False):
    '''
    Update old dict with items in new. If old[key] is a dict, update old[key]
    with new[key] to preserve existing keys in old[key].

        >>> merge({'a': {'x': 1}}, {'a': {'y': 2}})
        {'a': {'x': 1, 'y': 2}}

    If ``overwrite=True``, the old dict is overwritten. By default, a new
    deepcopy is created.
    '''
    result = old if overwrite else deepcopy(old)
    for key in new:
        if key in result and hasattr(result[key], 'items') and hasattr(new[key], 'items'):
            merge(old=result[key], new=new[key], overwrite=True)
        else:
            result[key] = new[key]
    return result


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
            merge(old=conf, new=config, overwrite=True)

        # Remove keys where the value is None
        for key, value, node in list(walk(conf)):
            if value is None:
                del node[key]

        return conf


def _yaml_open(path, default=AttrDict()):
    'Load a YAML path.Path as AttrDict. Replace {.} with path directory'
    path = path.absolute()
    if not path.exists():
        logging.warning('Missing config: %s', path)
        return default
    logging.debug('Loading config: %s', path)
    with path.open(encoding='utf-8') as handle:
        result = yaml.load(handle, Loader=AttrDictYAMLLoader)
    if result is None:
        logging.warning('Empty config: %s', path)
        return default
    for key, value, node in walk(result):
        if isinstance(value, string_types):
            if '{.}' in value:
                node[key] = value.replace('{.}', str(path.parent))
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
                    merge(old=node, new=new_conf, overwrite=True)
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
                logging.info('Deleted config: %s', imp.path)
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
