'Functions to process functions'

import yaml
import xmljson
import lxml.html
from .config import walk
from zope.dottedname.resolve import resolve
from orderedattrdict.yamlutils import AttrDictYAMLLoader


def build_transform(conf):
    '''
    Builds a new function based on a configuration object. The new function
    takes a single ``content`` argument and returns a transformed result.

    The configuration object may have these three keys:

    function
        name of a Python function to call. Defaults to the identity
        function, i.e. ``lambda x: x``.
    args
        list of positional arguments to pass to the function. ``"_"`` is
        replaced with ``content``. Unless specified, it defaults to ``["_"]`` --
        that is, the function takes ``content`` as its sole positional argument.
    kwargs
        keywords arguments to pass to the function. A value of ``"_"``
        is replaced with ``content``.

    For example, ``json(content, separators=[',', ':'])`` is defined as::

        function: json.dumps
        kwargs:
            separators: [',', ':']

    This is the same as::

        function: json.dumps
        args: ["_"]                 # This is the default
        kwargs:
            separators: [',', ':']

    If there are no ``args`` or ``kwargs``, the function is called directly with
    a single parameter -- the input. In other words, args defaults to [_]. This
    configuration defines ``str.lower``::

        function: str.lower
    '''

    # We create a Python string that contains the function. This is to speed
    # things up by pre-compiling and avoiding if conditions.
    result = ['def transform(content):']

    # If there's an "_" in args, replace that with the content
    args = list(conf.get('args', ['_']))
    for index, arg in enumerate(args):
        if arg == '_':
            result.append('\targs[%d] = content' % index)

    # If there's an "_" in kwargs, replace that with the content
    kwargs = dict(conf.get('kwargs', {}))
    for key, arg in kwargs.items():
        if arg == '_':
            result.append('\tkwargs[%s] = content' % repr(key))

    # If no function is defined, use the identity function. Else, compile it
    # in the global context
    if 'function' not in conf:
        result.append('\treturn content')
        doc = 'Return content as-is'
        name = 'identity'
        function = None
    else:
        result.append('\treturn function(*args, **kwargs)')
        function = resolve(conf['function'])
        doc = conf['function'].__doc__
        name = conf['function']

    # Compile the function
    context = {'args': args, 'kwargs': kwargs, 'function': function}
    exec('\n'.join(result), context)

    function = context['transform']
    function.__name__ = name
    function.__doc__ = doc
    return function


def badgerfish(content, mapping={}, doctype='<!DOCTYPE html>'):
    '''
    A transform that converts string content to YAML, then maps nodes
    using other functions, and renders the output as HTML.
    '''
    data = yaml.load(content, Loader=AttrDictYAMLLoader)
    maps = {tag: build_transform(trans) for tag, trans in mapping.items()}
    for tag, value, node in walk(data):
        if tag in maps:
            node[tag] = maps[tag](value)
    return lxml.html.tostring(xmljson.badgerfish.etree(data)[0], doctype=doctype)
