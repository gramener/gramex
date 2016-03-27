'Functions to process functions'

import six
import yaml
import xmljson
import lxml.html
import tornado.gen
import tornado.concurrent
from pydoc import locate
from orderedattrdict import AttrDict
from orderedattrdict.yamlutils import AttrDictYAMLLoader

from .config import walk, load_imports


def _arg_repr(arg):
    '''
    Arguments starting with ``=`` are converted into the variable. Otherwise,
    values are treated as strings. For example, ``=x`` is the variable ``x`` but
    ``x`` is the string ``"x"``. ``==x`` is the string ``"=x"``.
    '''
    if isinstance(arg, six.string_types) and len(arg) > 1:
        if arg[0] == '=':
            return repr(arg[1:]) if arg[1] == '=' else arg[1:]
    return repr(arg)


def build_transform(conf, vars={}, _coroutine=True):
    '''
    Converts a YAML function configuration into a callable function. For e.g.::

        function: json.dumps
        args: ["x"]
        kwargs:
            separators: [",", ":"]

    translates to::

        fn = build_transform(conf={
            'function': 'json.dumps',
            'args': ['x']
            'kwargs': {'separators': [',', ':']}
        })

    which becomes::

        def transform(_val):
            return json.dumps(
                'x',
                separators=[',', ':']
            )

    The returned function takes a single argument by default. You can change the
    arguments it accepts using ``vars``. For example::

        fn = build_transform(..., vars={'x': None, 'y': 1})

    creates::

        def transfom(x=None, y=1)

    In the ``conf`` parameter, ``args`` and ``kwargs`` values are interpreted
    literally. But values starting with ``=`` like ``=args`` are treated as
    variables. (Start ``==`` to represent a string that begins with ``=``.) For
    example, when this is called with ``vars={"args": {}}``::

        function: json.dumps
        args: '=args["data"]'
        kwargs:
            separators:
                - =args["comma"]
                - =args["colon"]

    becomes::

        def transform(args={}):
            return json.dumps(
                args["data"],
                separators=[args["comma"], args["colon"]]
            )
    '''

    # The returned function takes a single argument by default
    if not vars:
        vars = {'_val': None}

    if 'function' not in conf:
        raise KeyError('No function in conf %s' % conf)

    function = locate(conf['function'])
    if function is None:
        raise NameError('Cannot find function %s' % conf['function'])
    doc = function.__doc__
    name = conf['function']

    # Create the following code:
    #   def transform(var=default, var=default, ...):
    #       result = function(arg, arg, kwarg=value, kwarg=value, ...)
    body = [
        'def transform(',
        ', '.join('{:s}={!r:}'.format(var, val) for var, val in vars.items()),
        '):\n',
        '\tresult = function(\n',
    ]

    # If args is a string, convert to a list with that string
    # If args is not specified, use vars' keys as args
    if 'args' in conf:
        args = conf['args']
        args = [args] if isinstance(args, six.string_types) else list(args)
    else:
        args = ['=%s' % var for var in vars.keys()]

    # Add the function, arguments, and kwargs
    for arg in args:
        body.append('\t\t%s,\n' % _arg_repr(arg))
    for key, val in conf.get('kwargs', {}).items():
        body.append('\t\t%s=%s,\n' % (key, _arg_repr(val)))

    # If the result is a future,  yield it. Else, return it.
    body += [
        '\t)\n',
        '\tif is_future(result): result = yield result\n',
        '\traise Return(result)',
    ]

    # Compile the function with context variables
    context = {
        'function': function,
        'is_future': tornado.concurrent.is_future,
        'Return': tornado.gen.Return
    }
    exec(''.join(body), context)

    # Return the transformed function
    function = context['transform']
    # Convert it into a coroutine if _coroutine is True (default). But test
    # cases may pass _coroutine=False to test the raw conversion functionality.
    if _coroutine:
        function = tornado.gen.coroutine(function)
    function.__name__ = name
    function.__doc__ = doc
    return function


@tornado.gen.coroutine
def badgerfish(content, handler=None, mapping={}, doctype='<!DOCTYPE html>'):
    '''
    A transform that converts string content to YAML, then maps nodes
    using other functions, and renders the output as HTML.

    The specs for this function are in progress.
    '''
    data = yaml.load(content, Loader=AttrDictYAMLLoader)
    if handler is not None and hasattr(handler, 'file'):
        load_imports(data, handler.file)
    maps = {tag: build_transform(trans) for tag, trans in mapping.items()}
    for tag, value, node in walk(data):
        if tag in maps:
            node[tag] = yield maps[tag](value)
    raise tornado.gen.Return(lxml.html.tostring(xmljson.badgerfish.etree(data)[0],
                                                doctype=doctype, encoding='unicode'))
