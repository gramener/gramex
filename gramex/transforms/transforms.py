import six
import json
import tornado.gen
from types import GeneratorType
from orderedattrdict import AttrDict
from gramex.config import app_log, locate, variables


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


def build_transform(conf, vars=None, filename='transform'):
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

    ``build_transform`` also takes an optional ``name=`` parameter that defines
    the "filename" of the returned function. This is useful for log messages.

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

    if 'args' in conf:
        args = conf['args']
        # If args is not a list, convert to a list with that value
        if not isinstance(args, list):
            args = [args]
    else:
        # If args is not specified, use vars' keys as args
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
    code = compile(''.join(body), filename=filename, mode='exec')
    exec(code, context)

    # Return the transformed function
    function = context['transform']
    function.__name__ = str(name)
    function.__doc__ = str(doc)

    # Cache the result and return it
    _build_transform_cache[cache_key] = function
    return function


def condition(*args):
    '''
    Variables can also be computed based on conditions

    variables:
        OS:
            default: 'No OS variable defined'
        PORT:
            function: condition
            args:
                - $OS.startswith('Windows')
                - 9991
                - $OS.startswith('Linux')
                - 9992
                - 8883
    '''
    from string import Template
    var_defaults = {}
    for var in variables:
        var_defaults[var] = "variables.get('%s', '')" % var
    # could use iter, range(.., 2)
    if len(args) == 1 and isinstance(args[0], dict):
        pairs = args[0].items()
    else:
        pairs = zip(args[0::2], args[1::2])
    for cond, val in pairs:
        if isinstance(cond, six.string_types):
            if eval(Template(cond).substitute(var_defaults)):
                return val
        elif bool(cond):
            return val

    # If none of the conditions matched, we'll be here.
    # If there are an odd number of arguments and there's at least one condition,
    # treat the last as a default.
    if len(args) % 2 == 1 and len(args) > 2:
        return args[-1]


def flattener(fields, default=None, filename='flatten'):
    '''
    Generates a function that flattens deep dictionaries. For example::

        >>> flat = flattener({
                'id': 'id',
                'name': 'user.screen_name'
            })
        >>> flat({'id': 1, 'user': {'screen_name': 'name'}})
        {'id': 1, 'name': 'name'}

    Fields map as follows::

        ''    => obj
        True  => obj
        1     => obj[1]
        'x'   => obj['x']
        'x.y' => obj['x']['y']
        '1.x' => obj[1]['x']

    Missing values map to ``None``. You can change ``None`` to '' passing a
    ``default=''`` or any other default value.
    '''
    body = [
        'def %s(obj):\n' % filename,
        '\tr = AttrDict()\n',
    ]

    def assign(field, target, catch_errors=False):
        field = repr(field)
        if catch_errors:
            body.append('\ttry: r[%s] = %s\n' % (field, target))
            body.append('\texcept (KeyError, TypeError, IndexError): r[%s] = default\n' % field)
        else:
            body.append('\tr[%s] = %s\n' % (field, target))

    for field, source in fields.items():
        if not isinstance(field, six.string_types):
            app_log.error('flattener:%s: key %s is not a str', filename, field)
            continue
        if isinstance(source, six.string_types):
            target = 'obj'
            if source:
                for item in source.split('.'):
                    target += ('[%s]' if item.isdigit() else '[%r]') % item
            assign(field, target, catch_errors=True)
        elif source is True:
            assign(field, 'obj')
        elif isinstance(source, int) and not isinstance(source, bool):
            assign(field, 'obj[%d]' % source, catch_errors=True)
        else:
            app_log.error('flattener:%s: value %s is not a str/int', filename, source)
            continue
    body.append('\treturn r')
    code = compile(''.join(body), filename='flattener:%s' % filename, mode='exec')
    context = {'AttrDict': AttrDict, 'default': default}
    eval(code, context)
    return context[filename]
