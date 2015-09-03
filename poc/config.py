'''
Manage configuration loading
'''
import yaml
import logging
import logging.config
from pathlib import Path
from orderedattrdict import AttrDict, AttrDictYAMLLoader


def open(path, default=AttrDict()):
    'Load a YAML path.Path as an ordered AttrDict'
    if not path.exists():
        logging.warn('Cannot find YAML config: %s', path)
        return default
    result = yaml.load(path.open(), Loader=AttrDictYAMLLoader)
    if result is None:
        logging.warn('Empty YAML config: %s', path)
        return default
    return result


def walk(node):
    'Top-down recursive walk through nodes yielding key, value, node'
    for key, value in node.items():
        yield key, value, node
        if hasattr(value, 'items'):
            yield from walk(value)


def imports(node, root):
    '''
    Parse import: in the node relative to the root location.
    Return imported paths in the order they were imported.
    '''
    imported_paths = []
    for key, value, node in walk(node):
        if key == 'import':
            for name, pattern in value.items():
                paths = root.glob(pattern) if '*' in pattern else [Path(pattern)]
                for path in paths:
                    new_conf = open(path)
                    imported_paths += [path] + imports(new_conf, root=path)
                    node.update(new_conf)
            del node[key]
    return imported_paths


def load(path=None):
    if path is None:
        path = Path('.') / 'gramex.yaml'
    config = open(path)
    imports(config, path.absolute().parent)

    # TODO: apply any dynamic configurations
    # TODO: delete None values

    # TODO: Assertions and validations
    assert config.version == 1.0

    return config
