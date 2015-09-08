'Manages YAML config files as layered configurations with imports.'

import yaml
import logging
from pathlib import Path
from confutil import walk
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader


class ChainConfig(AttrDict):
    '''
    An AttrDict that manages multiple configurations as layers.

        >>> config = ChainConfig([
        ...     ('base', PathConfig('gramex.yaml')),
        ...     ('app1', PathConfig('app.yaml')),
        ...     ('app2', AttrDict())
        ... ])

    Any dict-compatible values are allowed. `+config` returns the merged values.
    '''

    def __pos__(self):
        '+config returns layers merged in order, removing null keys'
        conf = AttrDict()
        for name, config in self.items():
            if hasattr(config, '__pos__'):
                config.__pos__()
            conf.update(config)

        # Remove keys where the value is None
        for key, value, node in walk(conf):
            if value is None:
                del node[key]

        return conf


def open(path, default=AttrDict()):
    'Load a YAML path.Path as an ordered AttrDict'
    if not path.exists():
        logging.warn('Missing config: %s', path)
        return default
    logging.debug('Loading config: %s', path)
    with path.open() as handle:
        result = yaml.load(handle, Loader=AttrDictYAMLLoader)
    if result is None:
        logging.warn('Empty config: %s', path)
        return default
    return result


def pathstat(path):
    'Freeze path along current status, returning an AttrDict'
    return AttrDict(path=path, stat=path.stat() if path.exists() else None)


# TODO: Generalise load-processing
def imports(node, source):
    '''
    Parse import: in the node relative to the source path.
    Return imported pathtime in the order they were imported.
    '''
    imported_paths = [pathstat(source)]
    root = source.absolute().parent
    for key, value, node in walk(node):
        if key == 'import':
            for name, pattern in value.items():
                paths = root.glob(pattern) if '*' in pattern else [Path(pattern)]
                for path in paths:
                    new_conf = open(path)
                    imported_paths += [pathstat(path)] + imports(new_conf, source=path)
                    node.update(new_conf)
            # Delete the import key
            del node[key]
    return imported_paths


class PathConfig(AttrDict):
    '''
    `conf = PathConfig(path)` loads the YAML file at `path` as an AttrDict.
    `+conf` reloads the path if required.

    Like http://configure.readthedocs.org/ but supports imports not inheritance.
    This lets us import YAML files in the middle of a YAML structure.
    '''
    def __init__(self, path):
        super(PathConfig, self).__init__()
        self.__info__ = AttrDict(path=Path(path), imports=[])
        self.__pos__()

    def __pos__(self):
        '+config reloads a layer named name (if it has a path)'
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
            if exists and imp.path.stat().st_mtime > imp.stat.st_mtime:
                reload = True
                logging.info('Updated config: %s', imp.path)
                break
        if not reload:
            return self

        # If the main path itself is missing, warn and don't reload
        if not path.exists():
            logging.warn('Missing config: %s', path)
            return self

        self.clear()
        self.update(open(path))
        self.__info__.imports = imports(self, path)
        return self
