import ast
import datetime
import importlib
import json
import os
import time
import tornado.gen
import yaml
from functools import wraps
from types import GeneratorType
from orderedattrdict import AttrDict
from gramex.config import app_log, locate, variables, CustomJSONEncoder


def identity(x):
    return x


def _arg_repr(arg):
    '''
    Arguments starting with ``=`` are converted into the variable. Otherwise,
    values are treated as strings. For example, ``=x`` is the variable ``x`` but
    ``x`` is the string ``"x"``. ``==x`` is the string ``"=x"``.
    '''
    if isinstance(arg, str):
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
        function: _val.type         # Returns _val.type
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
    # the function: under it.
    if not hasattr(conf, 'items'):
        raise ValueError(f'{filename}: needs "function:". Got {conf!r}')

    conf = {key: val for key, val in conf.items() if key in {'function', 'args', 'kwargs'}}

    # The returned function takes a single argument by default
    if vars is None:
        vars = {'_val': None}

    if 'function' not in conf or not conf['function']:
        raise KeyError(f'{filename}: No function in conf {conf}')

    # Get the name of the function in case it's specified as a function call
    # expr is the full function / expression, e.g. str("abc")
    # tree is the ast result
    expr = conf['function']
    tree = ast.parse(expr)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
        raise ValueError(f'{filename}: function: must be Python function or expr, not {expr}')

    # Check whether to use the expression as is, or construct the expression
    # If expr is like "x" or "module.x", construct it if it's callable
    # Else, use the expression as-is
    function_name = _full_name(tree.body[0].value)
    module_name = function_name.split('.')[0] if isinstance(function_name, str) else None
    function, doc = None, expr
    # If the module or function is one of the vars themselves, return it as-is
    # _val.type will be used as-is, then, rather than looking for an "_val" module
    if module_name in vars:
        expr = function_name
    elif function_name is not None:
        function = locate(function_name, modules=['gramex.transforms'])
        doc = function.__doc__
        if function is None:
            app_log.error(f'{filename}: Cannot load function {function_name}')
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
                args = [f'={var}' for var in vars.keys()]
            # Add the function, arguments, and kwargs
            expr = function_name + '('
            for arg in args:
                expr += f'{_arg_repr(arg)}, '
            for key, val in conf.get('kwargs', {}).items():
                expr += f'{key}={_arg_repr(val)}, '
            expr += ')'
    # If expr starts with a function call (e.g. module.func(...)), use it's docs
    elif isinstance(tree.body[0].value, ast.Call):
        from astor import to_source
        doc = locate(to_source(tree.body[0].value.func).strip()).__doc__

    # Create the code
    modules = module_names(tree, vars)
    modulestr = ', '.join(sorted(modules))
    body = [
        'def transform(', ', '.join('{:s}={!r:}'.format(k, v) for k, v in vars.items()), '):\n',
        f'\timport {modulestr}\n' if modulestr else '',
        f'\treload_module({modulestr})\n' if modulestr and not cache else '',
        f'\tresult = {expr}\n',
        # If the result is a generator object, return it. Else, create a list and
        # return that. This ensures that the returned value is always an iterable
        '\treturn result if isinstance(result, GeneratorType) else [result,]' if iter else
        '\treturn result',
    ]

    # Compile the function with context variables
    import gramex.transforms
    from gramex.cache import reload_module
    context = dict(
        reload_module=reload_module,
        GeneratorType=GeneratorType,
        Return=tornado.gen.Return,
        AttrDict=AttrDict,
        **{key: getattr(gramex.transforms, key) for key in gramex.transforms.__all__}
    )
    code = compile(''.join(body), filename=filename, mode='exec')
    # exec() is safe here since the code is written by app developer
    exec(code, context)     # nosec: developer-initiated

    # Return the transformed function
    result = context['transform']
    result.__name__ = str(function_name or filename)
    result.__doc__ = str(doc)
    result.__func__ = function

    return result


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
        var_defaults[var] = f"variables.get('{var}', '')"
    # could use iter, range(.., 2)
    if len(args) == 1 and isinstance(args[0], dict):
        pairs = args[0].items()
    else:
        pairs = zip(args[0::2], args[1::2])
    for cond, val in pairs:
        if isinstance(cond, str):
            # eval() is safe here since `cond` is written by app developer
            if eval(Template(cond).substitute(var_defaults)):    # nosec: developer-initiated
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
        f'def {filename}(obj):\n',
        '\tr = AttrDict()\n',
    ]

    def assign(field, target, catch_errors=False):
        field = repr(field)
        if catch_errors:
            body.append(f'\ttry: r[{field}] = {target}\n')
            body.append(f'\texcept (KeyError, TypeError, IndexError): r[{field}] = default\n')
        else:
            body.append(f'\tr[{field}] = {target}\n')

    for field, source in fields.items():
        if not isinstance(field, str):
            app_log.error(f'flattener:{filename}: key {field} is not a str')
            continue
        if isinstance(source, str):
            target = 'obj'
            if source:
                for item in source.split('.'):
                    target += ('[%s]' if item.isdigit() else '[%r]') % item
            assign(field, target, catch_errors=True)
        elif source is True:
            assign(field, 'obj')
        elif isinstance(source, int) and not isinstance(source, bool):
            assign(field, f'obj[{source}]', catch_errors=True)
        else:
            app_log.error(f'flattener:{filename}: value {source} is not a str/int')
            continue
    body.append('\treturn r')
    code = compile(''.join(body), filename=f'flattener:{filename}', mode='exec')
    context = {'AttrDict': AttrDict, 'default': default}
    # eval() is safe here since the code is constructed entirely in this function
    eval(code, context)     # nosec: developer-initiated
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


# int(x), float(x), str(x) do a good job of converting strings to respective types.
# But not all types work smoothly. Handle them here.
_convert_map = {
    # bool("true") fails Use yaml.safe_load in such cases
    bool: lambda x: yaml.safe_load(x) if isinstance(x, (str, bytes)) else x,
    # NoneType("None") doesn't work either. Just return None
    type(None): lambda x: None,
    # TODO: Convert dates but without importing pandas on startup
    # datetime.datetime: lambda x: pd.to_datetime(x).to_pydatetime,
}


def typelist(hint):
    typ, is_list = hint, False
    # If typ is an Annotation, use the native type. Else use the type.
    while hasattr(typ, '__args__'):
        is_list = getattr(typ, '_name', None) in ('List', 'Tuple')
        typ = typ.__args__[0]
    return typ, is_list


def convert(hint, param, *args):
    from pandas.core.common import flatten
    args = list(flatten(args))
    typ, is_list = typelist(hint)
    # Convert args to the native type
    method = _convert_map.get(typ, typ)
    # If default is list-like or hint is List-like, return list. Else return last value
    if is_list or isinstance(param.default, (list, tuple)):
        return [method(arg) for arg in args]
    else:
        return method(args[-1] if len(args) else param.default)


class Header(str):
    pass


def handler(func):
    """Wrap a function to make it compatible with a tornado.web.RequestHandler

    Use this decorator to expose a function as a REST API, with path or URL parameters mapped to
    function arguments with type conversion.

    Suppose you have the following function in ``greet.py``::

        @handler
        def birthday(name: str, age: int):
            return f'{name} turns {age:d} today! Happy Birthday!'

    Then, in ``gramex.yaml``, you can use it as a FunctionHandler as follows::

        url:
            pattern: /$YAMLURL/greet
            handler: FunctionHandler
            kwargs:
                function: greet.birthday

    Now, ``/greet?name=Gramex&age=0010`` returns "Gramex turns 10 today! Happy Birthday!".
    It converts the URL parameters into the types found in the annotations, e.g. `0010` into 10.

    An alternate way of configuring this is as follows::

        url:
            pattern: /$YAMLURL/greet/name/(.*)/age/(.*)
            handler: FunctionHandler
            kwargs:
                # You can pass name=... and age=... as default values
                # but ensure that handler is the first argument in the config.
                function: greet.birthday(handler, name='Name', age=10)

    Now, ``/greet/name/Gramex/age/0010`` returns "Gramex turns 10 today! Happy Birthday!".

    The function args and kwargs are taken from these sources this in order.

    1. From the YAML function, e.g. ``function: greet.birthday('Name', age=10)`` sets
       ``name='Name'`` and ``age=10``
    2. Over-ridden by YAML URL pattern, e.g. ``pattern: /$YAMLPATH/(.*)/(?P<age>.*)`` when called
       with ``/greet/Name/10`` sets ``name='Name'`` and ``age=10``
    3. Over-ridden by URL query parameters, e.g. ``/greet?name=Name&age=10`` sets ``name='Name'``
       and ``age=10``
    4. Over-ridden by URL POST body parameters, e.g. ``curl -X POST /greet -d "?name=Name&age=10"``
       sets ``name='Name'`` and ``age=10``

    ``handler`` is also available as a kwarg. You can use this as the last positional argument or
    a keyword argument. Both ``def birthday(name, age, handler)`` and
    ``def birthday(name, age, handler=None)`` are valid.
    """
    from inspect import signature
    from typing import get_type_hints
    from pandas.core.common import flatten

    params = signature(func).parameters
    hints = get_type_hints(func)

    @wraps(func)
    def wrapper(handler, *cfg_args, **cfg_kwargs):
        # We'll create a (*args, **kwargs)
        # College args from the config `args:` and then the handler pattern /(.*)/(.*)
        req_args = list(cfg_args) + handler.path_args
        # Collect kwargs from the config `kwargs:` and then the handler pattern /(?P<key>.*)
        # and the the URL query params
        req_kwargs = {'handler': handler}
        for d in (cfg_kwargs, handler.path_kwargs, handler.args):
            req_kwargs.update(d)
        headers = handler.request.headers
        # If POSTed with Content-Type: application/json, parse body as well
        if headers.get('Content-Type', '') == 'application/json':
            req_kwargs.update(json.loads(handler.request.body))

        # Map these into the signature
        args, kwargs = [], {}
        for arg, param in params.items():
            hint = hints.get(arg, identity)
            # If hint says it's a header, pass the header without converting
            if hint is Header:
                kwargs[arg] = handler.request.headers.get(arg)
                continue
            # Populate positional arguments first, if any
            if len(req_args):
                # If function takes a positional arg, assign first req_arg
                if param.kind in {param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD}:
                    args.append(convert(hint, param, req_args.pop(0)))
                # If it's a *arg, assign all remaining req_arg
                elif param.kind == param.VAR_POSITIONAL:
                    for val in req_args:
                        args.append(convert(hint, param, val))
                    req_args.clear()
            # Also populate keyword arguments from req_kwargs if there's a match
            if arg in req_kwargs:
                # Pop any keyword argument that matches the function argument
                if param.kind in {param.KEYWORD_ONLY, param.POSITIONAL_OR_KEYWORD}:
                    kwargs[arg] = convert(hint, param, req_kwargs.pop(arg))
                # If its a *arg, assign all remaining values
                elif param.kind == param.VAR_POSITIONAL:
                    for val in flatten([req_kwargs.pop(arg)]):
                        args.append(convert(hint, param, val))

        return func(*args, **kwargs)

    wrapper.__func__ = func
    return wrapper


def build_log_info(keys, *vars):
    '''
    Creates a ``handler.method(vars)`` that returns a dictionary of computed
    values. ``keys`` defines what keys are returned in the dictionary. The values
    are computed using the formulas in the code.
    '''
    from gramex import conf

    # Define direct keys. These can be used as-is
    direct_vars = {
        'name': 'handler.name',
        'class': 'handler.__class__.__name__',
        'time': 'round(time.time() * 1000, 0)',
        'datetime': 'datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")',
        'method': 'handler.request.method',
        'uri': 'handler.request.uri',
        'ip': 'handler.request.remote_ip',
        'status': 'handler.get_status()',
        'duration': 'round(handler.request.request_time() * 1000, 0)',
        'port': 'conf.app.listen.port',
        # TODO: get_content_size() is not available in RequestHandler
        # 'size': 'handler.get_content_size()',
        'user': '(handler.current_user or {}).get("id", "")',
        'session': 'handler.session.get("id", "")',
        'error': 'getattr(handler, "_exception", "")',
    }
    # Define object keys for us as key.value. E.g. cookies.sid, user.email, etc
    object_vars = {
        'args': 'handler.get_argument("{val}", "")',
        'request': 'getattr(handler.request, "{val}", "")',
        'headers': 'handler.request.headers.get("{val}", "")',
        'cookies': 'handler.request.cookies["{val}"].value ' +
                   'if "{val}" in handler.request.cookies else ""',
        'user': '(handler.current_user or {{}}).get("{val}", "")',
        'env': 'os.environ.get("{val}", "")',
    }
    vals = []
    for key in keys:
        if key in vars:
            vals.append('"{}": {},'.format(key, key))
            continue
        if key in direct_vars:
            vals.append('"{}": {},'.format(key, direct_vars[key]))
            continue
        if '.' in key:
            prefix, value = key.split('.', 2)
            if prefix in object_vars:
                vals.append('"{}": {},'.format(key, object_vars[prefix].format(val=value)))
                continue
        app_log.error(f'Skipping unknown key {key}')
    code = compile('def fn(handler, %s):\n\treturn {%s}' % (', '.join(vars), ' '.join(vals)),
                   filename='log', mode='exec')
    context = {'os': os, 'time': time, 'datetime': datetime, 'conf': conf, 'AttrDict': AttrDict}
    # exec() is safe here since the code is constructed entirely in this function
    exec(code, context)     # nosec: developer-initiated
    return context['fn']
