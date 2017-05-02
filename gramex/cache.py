'''Caching utilities'''
import io
import os
import six
import json
import yaml
import pandas as pd
from gramex.config import app_log


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
    text=_opener(lambda handle: handle.read()),
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

    - ``text``: reads files using io.open
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

        # Load data using a custom callback
        open('data.fmt', my_format_reader_function, arg='value')
    '''
    # Pass _reload_status = True for testing purposes. This returns a tuple:
    # (result, reloaded) instead of just the result.
    _reload_status = kwargs.pop('_reload_status', False)
    reloaded = False

    mtime = os.stat(path).st_mtime
    _cache = kwargs.pop('_cache', _DEFAULT_CACHE)
    callback_is_str = isinstance(callback, six.string_types)
    key = (path, callback if callback_is_str else id(callback))
    if key not in _cache or mtime > _cache[key]['mtime']:
        reloaded = True
        if callable(callback):
            data = callback(path, **kwargs)
        elif callback_is_str:
            method = _CALLBACKS.get(callback)
            if method is not None:
                data = method(path, **kwargs)
            else:
                raise TypeError('gramex.cache.open(callback="%s") is not a known type', callback)
        else:
            raise TypeError('gramex.cache.open(callback=) must be a function, not %r', callback)
        _cache[key] = {'data': data, 'mtime': mtime}

    result = _cache[key]['data']
    return (result, reloaded) if _reload_status else result


# Date of file when module was last loaded. Used by reload_module
_reload_dates = {}


def reload_module(*modules):
    '''
    Reloads one or more modules if they are outdated, i.e. only if required the
    underlying source file has changed.

    For example::

        import mymodule             # Load cached module
        reload_module(mymodule)     # Reload module if the source has changed

    This is most useful during template development. If your changes are in a
    Python module, then adding these lines will pick up new module changes when
    the template is re-run::

        {% import mymodule %}
        {% set reload_module(mymodule) %}
    '''
    for module in modules:
        name = getattr(module, '__name__', None)
        path = getattr(module, '__file__', None)
        if name is None or path is None or not os.path.exists(path):
            app_log.warn('Path for module %s is %s: not found', name, path)
            continue
        mtime = os.stat(path).st_mtime
        if _reload_dates.get(name, 0) >= mtime:
            continue
        app_log.info('Reloading module %s', name)
        six.moves.reload_module(module)
        _reload_dates[name] = mtime
