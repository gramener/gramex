import six
import json
import tornado.gen
from types import GeneratorType
from orderedattrdict import AttrDict
from ..config import locate


def _arg_repr(arg):
    '''
    Arguments starting with ``=`` are converted into the variable. Otherwise,
    values are treated as strings. For example, ``=x`` is the variable ``x`` but
    ``x`` is the string ``"x"``. ``==x`` is the string ``"=x"``.
    '''
    if isinstance(arg, six.string_types):
        if arg.startswith('=='):
            return repr(arg[1:])        # "==x" becomes '"=x"'
        elif arg.startswith('='):
            return arg[1:]              # "=x" becomes 'x'
    return repr(arg)                    # "x" becomes '"x"', 1 becomes '1', etc


_build_transform_cache = {}


def build_transform(conf, vars=None):
    '''
    Converts a function configuration into a callable function. For e.g.::

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
            result = json.dumps(
                'x',
                separators=[',', ':']
            )
            return result if isinstance(result, GeneratorType) else (result,)

    The returned function takes a single argument by default. You can change the
    arguments it accepts using ``vars``. For example::

        fn = build_transform(..., vars={'x': None, 'y': 1})

    creates::

        def transfom(x=None, y=1):

    Or pass ``vars={}`` for function that does not accept any parameters.

    The returned function always returns an iterable containing the values. If
    the function returns a single value, you can get it on the first iteration.
    If the function returns a generator object, that is returned as-is.

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
    # Ensure that the transform is a dict. This is a common mistake. We forget
    # the pattern: prefix
    if not hasattr(conf, 'items'):
        raise ValueError('transform: needs {pattern: spec} dicts, but got %s' % repr(conf))

    # If the input is already cached, return it.
    conf = {key: val for key, val in conf.items() if key in {'function', 'args', 'kwargs'}}
    cache_key = json.dumps(conf), json.dumps(vars)
    if cache_key in _build_transform_cache:
        return _build_transform_cache[cache_key]

    # The returned function takes a single argument by default
    if vars is None:
        vars = {'_val': None}

    if 'function' not in conf:
        raise KeyError('No function in conf %s' % conf)

    function = locate(conf['function'], modules=['gramex.transforms'])
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

    # If the result is a generator object, return it. Else, create a tuple and
    # return that. This ensures that the returned value is always an iterable
    body += [
        '\t)\n',
        '\treturn result if isinstance(result, GeneratorType) else (result,)',
    ]

    # Compile the function with context variables
    context = {
        'function': function,
        'GeneratorType': GeneratorType,
        'Return': tornado.gen.Return,
        'AttrDict': AttrDict
    }
    exec(''.join(body), context)

    # Return the transformed function
    function = context['transform']
    function.__name__ = name
    function.__doc__ = doc

    # Cache the result and return it
    _build_transform_cache[cache_key] = function
    return function
