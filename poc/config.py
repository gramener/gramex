'''
Manages YAML config files as layered configurations with imports.

Create a new LayeredConfig, initialised with 0 or more layers. Each layer
has a name (required) and a path to load from (optional.)

This creates a config with 2 layers: base and app (initialised from app.yaml)

    >>> config = LayeredConfig('base', ('app', 'app.yaml'))

The same can also be written using the overloaded += operator:

    >>> config = LayeredConfig()
    >>> config += 'base'
    >>> config += ('app', 'app.yaml')

Once created, the layers act as attributes.

    >>> config.base.key = value
    >>> config.app.key = value

To reload and get the merged values, use the unary + operator:

    >>> +config

This is similar to http://configure.readthedocs.org/ but supports imports
instead of inheritence. This lets us import YAML files in the middle of a YAML
structure.
'''

import yaml
import logging
from pathlib import Path
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader


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


def walk(node):
    'Top-down recursive walk through nodes yielding key, value, node'
    for key, value in node.items():
        yield key, value, node
        if hasattr(value, 'items'):
            for item in walk(value):
                yield item


def pathinfo(path):
    'Return the {path:, mtime:} structure. mtime is 0 of path is missing'
    mtime = path.stat().st_mtime if path.exists() else 0
    return AttrDict(path=path, mtime=mtime)


# TODO: Generalise into different kinds of post-processing
def imports(node, root):
    '''
    Parse import: in the node relative to the root location.
    Return imported pathinfo in the order they were imported.
    '''
    imported_paths = []
    for key, value, node in walk(node):
        if key == 'import':
            for name, pattern in value.items():
                paths = root.glob(pattern) if '*' in pattern else [Path(pattern)]
                for path in paths:
                    new_conf = open(path)
                    imported_paths += [pathinfo(path)] + imports(new_conf, root=path)
                    node.update(new_conf)
            # Delete the import key
            del node[key]
    return imported_paths


class LayeredConfig(AttrDict):
    'Manages multiple configurations as layers, supporting imports'

    def __init__(self, *layers):
        'Initialise with 0 or more layers. A layer is a string or (str, path)'
        super(LayeredConfig, self).__init__()
        self.__layers__ = AttrDict()
        for layer in layers:
            self.__iadd__(layer)

    def __iadd__(self, layer):
        'Add a named layer. Optional config path is linked and loaded'
        if isinstance(layer, str):
            name, path = layer, None
        else:
            name, path = layer[:2]
        if name not in self.__layers__:
            self[name] = AttrDict()
            path = None if path is None else Path(path)
            self.__layers__[name] = AttrDict(name=name, path=path, imports=[])
            self.__load__(name)
        return self

    def __pos__(self):
        '+config returns layers merged in order, removing null keys'
        conf = AttrDict()
        for name in self:
            self.__load__(name)
            conf.update(self[name])

        # Remove keys where the value is None
        # TODO: Generalise post-processing
        for key, value, node in walk(conf):
            if value is None:
                del node[key]

        return conf

    def __load__(self, name):
        'Reload a layer named name (if it has a path)'
        layer = self.__layers__[name]
        path = layer.path
        if path is None:
            return

        # We must reload the layer if nothing has been imported...
        reload = not layer.imports
        # ... or if an imported file is deleted / updated
        for imp in layer.imports:
            exists = imp.path.exists()
            if not exists and imp.mtime:
                reload = True
                logging.info('Deleted config: %s', imp.path)
                break
            if exists and imp.path.stat().st_mtime > imp.mtime:
                reload = True
                logging.info('Updated config: %s', imp.path)
                break
        if not reload:
            return

        # If the main path itself is missing, warn and don't reload
        if not path.exists():
            logging.warn('Missing path %s for config %s', path, name)
            return

        self[name] = open(path)
        layer.imports = [pathinfo(path)] + imports(self[name], path.absolute().parent)
