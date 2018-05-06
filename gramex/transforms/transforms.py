import ast
import six
import json
import importlib
import tornado.gen
import gramex.transforms
from types import GeneratorType
from orderedattrdict import AttrDict
from gramex.cache import reload_module
from gramex.config import app_log, locate, variables, CustomJSONEncoder


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


def _full_name(tree):
    '''Decompile ast tree for "x", "module.x", "package.module.x", etc'''
    if isinstance(tree, ast.Name):
        return tree.id
    elif isinstance(tree, ast.Attribute):
        parent = _full_name(tree.value)
        return parent + '.' + tree.attr if parent is not None else parent
    return None


def module_names(node, vars):
    '''
    Collects a list of modules mentioned in an AST tree. Ignores things in vars

    visitor = ModuleNameVisitor()
    visitor.visit(ast.parse(expression))
    visitor.modules
    '''
    context = []
    modules = set()

    def visit(node):
        if not hasattr(node, '_fields'):
            return
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Name):
                if len(context) and context[-1]:
                    module = [child.id]
                    for p in context[::-1]:
                        if p is not None:
                            module.append(p)
                        else:
                            break
                    if len(module) and module[0] not in vars:
                        module.pop()
                        while len(module):
                            module_name = '.'.join(module)
                            try:
                                importlib.import_module(module_name)
                                modules.add(module_name)
                                break
                            except ImportError:
                                module.pop()
                            # Anything other than an ImportError means we've identified the module.
                            # E.g. A SyntaxError means the file is right, it just has an error.
                            # Add these modules as well.
                            else:
                                modules.add(module_name)
                                break
            context.append(child.attr if isinstance(child, ast.Attribute) else None)
            visit(child)
            context.pop()

    visit(node)
    return modules


def build_transform(conf, vars=None, filename='transform', cache=False, iter=True):
    '''
    Converts an expression into a callable function. For e.g.::

        function: json.dumps("x", separators: [",", ":"])

    translates to::

        fn = build_transform(conf={
            'function': 'json.dumps("x", separators: [",", ":"])',
        })

    which becomes::

        def transform(_val):
            import json
            result = json.dumps("x", separators=[",", ":""])
            return result if isinstance(result, GeneratorType) else (result,)

    The same can also be achieved via::

        function: json.dumps
        args: ["x"]
        kwargs:
            separators: [",", ":"]

    Any Python expression is also allowed. The following are valid functions::

        function: 1                 # returns 1
        function: _val + 1          # Increments the input parameter by 1
        function: json.dumps(_val)  # Returns the input as a string
        function: json.dumps        # This is the same as json.dumps(_val)

    ``build_transform`` also takes an optional ``filename=`` parameter that sets
    the "filename" of the returned function. This is useful for log messages.

    It takes an optional ``cache=True`` that permanently caches the transform.
    The default is ``False`` that re-imports the function's module if changed.

    The returned function takes a single argument called ``_val`` by default. You
    can change the arguments it accepts using ``vars``. For example::

        fn = build_transform(..., vars={'x': None, 'y': 1})

    creates::

        def transform(x=None, y=1):
            ...

    Or pass ``vars={}`` for function that does not accept any parameters.

    The returned function returns an iterable containing the values. If the
    function returns a single value, you can get it on the first iteration. If
    the function returns a generator object, that is returned as-is.

    But if ``iter=False`` is passed, the returned function just contains the
    returned value as-is -- not as a list.

    In the ``conf`` parameter, ``args`` and ``kwargs`` values are interpreted
    literally. But values starting with ``=`` like ``=args`` are treated as
    variables. (Start ``==`` to represent a string that begins with ``=``.) For
    example, when this is called with ``vars={"handler": None}``::

        function: json.dumps
        args: =handler
        kwargs:
            key: abc
            name: =handler.name

    becomes::

        def transform(handler=None):
            return json.dumps(handler, key="abc", name=handler.name)
    '''
    # Ensure that the transform is a dict. This is a common mistake. We forget
    # the pattern: prefix
    if not hasattr(conf, 'items'):
        raise ValueError('%s: needs {function: name}. Got %s' % (filename, repr(conf)))

    conf = {key: val for key, val in conf.items() if key in {'function', 'args', 'kwargs'}}

    # The returned function takes a single argument by default
    if vars is None:
        vars = {'_val': None}

    if 'function' not in conf or not conf['function']:
        raise KeyError('%s: No function in conf %s' % (filename, conf))

    # Get the name of the function in case it's specified as a function call
    # expr is the full function / expression, e.g. six.text_type("abc")
    # tree is the ast result
    expr = conf['function']
    tree = ast.parse(expr)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
        raise ValueError('%s: function: must be an Python function or expression, not %s',
                         (filename, expr))

    # Check whether to use the expression as is, or construct the expression
    # If expr is like "x" or "module.x", construct it if it's callable
    # Else, use the expression as-is
    function_name = _full_name(tree.body[0].value)
    if function_name is not None:
        function = locate(function_name, modules=['gramex.transforms'])
        if function is None:
            app_log.error('%s: Cannot load function %s' % (filename, function_name))
        # This section converts the function into an expression.
        # We do this only if the original expression was a *callable* function.
        # But if we can't load the original function (e.g. SyntaxError),
        # treat that as a function as well, allowing users to correct it later.
        if callable(function) or function is None:
            if 'args' in conf:
                # If args is not a list, convert to a list with that value
                args = conf['args'] if isinstance(conf['args'], list) else [conf['args']]
            else:
                # If args is not specified, use vars' keys as args
                args = ['=%s' % var for var in vars.keys()]
            # Add the function, arguments, and kwargs
            expr = function_name + '('
            for arg in args:
                expr += '%s, ' % _arg_repr(arg)
            for key, val in conf.get('kwargs', {}).items():
                expr += '%s=%s, ' % (key, _arg_repr(val))
            expr += ')'

    # Create the code
    modules = module_names(tree, vars)
    modulestr = ', '.join(sorted(modules))
    body = [
        'def transform(', ', '.join('{:s}={!r:}'.format(k, v) for k, v in vars.items()), '):\n',
        '\timport %s\n' % modulestr if modulestr else '',
        '\treload_module(%s)\n' % modulestr if modulestr and not cache else '',
        '\tresult = %s\n' % expr,
        # If the result is a generator object, return it. Else, create a list and
        # return that. This ensures that the returned value is always an iterable
        '\treturn result if isinstance(result, GeneratorType) else [result,]' if iter else
        '\treturn result',
    ]

    # Compile the function with context variables
    context = dict(
        reload_module=reload_module,
        GeneratorType=GeneratorType,
        Return=tornado.gen.Return,
        AttrDict=AttrDict,
        **{key: getattr(gramex.transforms, key) for key in gramex.transforms.__all__}
    )
    code = compile(''.join(body), filename=filename, mode='exec')
    exec(code, context)         # nosec - OK to run arbitrary Python code in YAML

    # Return the transformed function
    function = context['transform']
    function.__name__ = str(function_name or filename)
    function.__doc__ = str(function.__doc__)

    return function


def condition(*args):
    '''
    DEPRECATED. Use the ``if`` construct in config keys instead.

    Variables can also be computed based on conditions::

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
            if eval(Template(cond).substitute(var_defaults)):    # nosec - any Python expr is OK
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
    eval(code, context)     # nosec - code constructed entirely in this function
    return context[filename]


_once_info = {}


def once(*args, **kwargs):
    '''
    Returns False if once() has been called before with these arguments. Else True.
    Data is stored in a persistent SQLite dict.
    '''
    if 'db' not in _once_info:
        import os
        from sqlitedict import SqliteDict
        dbpath = os.path.join(variables['GRAMEXDATA'], 'once.db')
        _once_info['db'] = SqliteDict(dbpath, tablename='once', autocommit=True)
    db = _once_info['db']
    key = json.dumps(args, separators=(',', ':'), cls=CustomJSONEncoder)
    if kwargs.get('_clear', False):
        if key in db:
            del db[key]
        return None
    if key in db:
        return False
    db[key] = True
    return True
