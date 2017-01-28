'''Caching utilities'''
import io
import os
import json
import yaml
import pandas as pd
from six import string_types


def _opener(callback):
    '''
    Converts method that accepts a handle into a method that accepts a file path.
    For example, ``jsonload = _opener(json.load)`` allows ``jsonload('x.json')``
    to return the parsed JSON contents of ``x.json``.

    Any keyword arguments applicable for ``io.open`` are passed to ``io.open``.
    All other arguments and keyword arguments are passed to the callback (e.g.
    json.load).
    '''
    open_defaults = dict(mode='r', buffering=-1, encoding='utf-8', errors='strict',
                         newline=None, closefd=True)

    def method(path, **kwargs):
        open_args = {key: kwargs.pop(key, val) for key, val in open_defaults.items()}
        with io.open(path, **open_args) as handle:
            return callback(handle, **kwargs)
    return method


_DEFAULT_CACHE = {}
_CALLBACKS = dict(
    yaml=_opener(yaml.load),
    json=_opener(json.load),
    csv=pd.read_csv,
    excel=pd.read_excel,
    hdf=pd.read_hdf,
    html=pd.read_html,
    sas=pd.read_sas,
    stata=pd.read_stata,
    table=pd.read_table,
)


def open(path, callback, **kwargs):
    '''
    Reads a file, processes it via a callback, caches the result and returns it.
    When called again, returns the cached result unless the file has updated.

    The callback can be a function that accepts the filename and any other
    arguments, or a string that can be one of

    - ``yaml``: reads files using PyYAML
    - ``json``: reads files using json.load
    - ``csv``, ``excel``, ``hdf``, ``html``, ``sas``, ``stata``, ``table``: reads using Pandas

    For example::

        # Load data.yaml as YAML into an AttrDict
        open('data.yaml', 'yaml')

        # Load data.json as JSON into an AttrDict
        open('data.json', 'json', object_pairs_hook=AttrDict)

        # Load data.csv as CSV into a Pandas DataFrame
        open('data.csv', 'csv', encoding='cp1252')
    '''
    # Pass _reload_status = True for testing purposes. This returns a tuple:
    # (result, reloaded) instead of just the result.
    _reload_status = kwargs.pop('_reload_status', False)
    reloaded = False

    mtime = os.stat(path).st_mtime
    _cache = kwargs.pop('_cache', _DEFAULT_CACHE)
    if path not in _cache or mtime > _cache[path]['mtime']:
        reloaded = True
        if callable(callback):
            data = callback(path, **kwargs)
        elif isinstance(callback, string_types):
            method = _CALLBACKS.get(callback)
            if method is not None:
                data = method(path, **kwargs)
            else:
                raise TypeError('gramex.cache.open(callback="%s") is not a known type', callback)
        else:
            raise TypeError('gramex.cache.open(callback=) must be a function, not %r', callback)
        _cache[path] = {'data': data, 'mtime': mtime}

    result = _cache[path]['data']
    return (result, reloaded) if _reload_status else result
