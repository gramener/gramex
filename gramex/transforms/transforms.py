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
from gramex.config import app_log, locate, variables, CustomJSONEncoder, merge
from typing import Union, Any, List


def identity(x):
    return x


def _arg_repr(arg):
    '''
    Arguments starting with `=` are converted into the variable. Otherwise,
    values are treated as strings. For example, `=x` is the variable `x` but
    `x` is the string `"x"`. `==x` is the string `"=x"`.
    '''
    if isinstance(arg, str):
        if arg.startswith('=='):
            return repr(arg[1:])  # "==x" becomes '"=x"'
        elif arg.startswith('='):
            return arg[1:]  # "=x" becomes 'x'
    return repr(arg)  # "x" becomes '"x"', 1 becomes '1', etc


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
            if isinstance(child, ast.Name) and len(context) and context[-1]:
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


def build_transform(
    conf: dict,
    vars: dict = None,
    kwargs: Union[bool, str] = False,
    filename: str = 'transform',
    cache: bool = False,
    iter: bool = True,
):
    '''Converts an expression into a callable function.

    Examples:
        >>> fn = build_transform({'function': 'json.dumps({"x": 1})'}, iter=False)
        >>> fn()
        ... '{"x": 1}'

    This compiles the expression into a callable function as follows:

    ```python
    def transform(_val):
        import json
        result = json.dumps({"x": 1})
        return result
    ```

    Parameters:
        conf: expression to compile
        vars: variables passed to the compiled function
        kwargs: `True` to accept **kwargs. Any string to define the kwargs variable name
        filename: filename to print in case of errors
        cache: `False` re-imports modules if changed. `True` caches module
        iter: `True` always returns an iterable. `False` returns a single value

    `conf` is a dict with a `function` key with Python expression. This expression is compiled
    and returned. If the expression uses modules (e.g. `json.dumps`), they are auto-imported.

    It optionally accepts an `args` list and a `kwargs` list if `function` is a function name.

    Examples:
        >>> {'function': '1'}               # => 1
        >>> {'function': 'x + y'}           # => x + y
        >>> {'function': 'json.dumps(x)'}   # => json.dumps(s)
        >>> {'function': 'json.dumps', 'args': ['x'], 'kwargs': {'indent': 2}}
        >>> {'function': 'json.dumps("x", indent=2)`    # same as above

    `args` values and `kwargs` keys are treated as strings, not variables. But values starting with
    `=` (e.g. `=handler`) are treated as variables. (Use `==x` to represent the string `=x`.)

    Examples:
        >>> {'function': 'str', 'args': ['handler']}      # => str('handler')
        >>> {'function': 'str', 'args': ['=handler']}     # => str(handler)
        >>> {'function': 'str', 'args': ['==handler']}    # => str('=handler')

    `vars` defines the compiled function's signature. `vars={'x': 1, 'y': 2}` creates a
    `def transform(x=1, y=2):`.

    `vars` defaults to `{'_val': None}`.

    Examples:
        >>> add = build_transform({'function': 'x + y'}, vars={'x': 1, 'y': 2}, iter=False)
        >>> add()
        ... 3
        >>> add(x=3)
        ... 5
        >>> add(x=3, y=4)
        ... 7
        >>> incr = build_transform({'function': '_val + 1'}, iter=False)
        >>> incr(3)
        ... 4

    `kwargs=True` allows the compiled function to accept any keyword arguments as `**kwargs`.
    Specify `kwargs='kw'` to use `kw` (or any string) as the keyword arguments variable instead.

    Examples:
        >>> params = build_transform({'function': 'kwargs'}, vars={}, kwargs=True, iter=False)
        >>> params(x=1)
        ... {'x': 1}
        >>> params(x=1, y=2)
        ... {'x': 1, 'y': 2}
        >>> params = build_transform({'function': 'kw'}, vars={}, kwargs='kw', iter=False)
        >>> params(x=1, y=2)
        ... {'x': 1, 'y': 2}

    `filename` defines the filename printed in error messages.

    Examples:
        >>> error = build_transform({'function': '1/0'}, filename='zero-error', iter=False)
        ... Traceback (most recent call last):
        ...   File "<stdin>", line 1, in <module>
        ...   File "zero-error", line 2, in transform
        ... ZeroDivisionError: division by zero

    `cache=False` re-imports the modules if changed. This is fairly efficient, and is the default.
    Use `cache=True` to cache modules until Python is restarted.

    `iter=True` always returns an iterable. If the `function` is a generator (i.e. has a `yield`),
    it is returned as-is. Else it is returned as an array, i.e. `[result]`.

    Examples:
        `build_transform()` returns results wrapped as an array.

        >>> val = build_transform({'function': '4'})
        >>> val()
        ... [4]
        >>> val = build_transform({'function': '[4, 5]'})
        >>> val()
        ... [[4, 5]]

        If the result is a generator, it is returned as-is.

        >>> def gen():
        ...     for x in range(5):
        ...         yield x
        >>> val = build_transform({'function': 'fn()'}, vars={'fn': None})
        >>> val(gen)
        ... <generator object gen at 0x....>
        >>> list(val(gen))
        ... [0, 1, 2, 3, 4]

        If `iter=False`, it returns the results as-is.

        >>> val = build_transform({'function': '4'}, iter=False)
        >>> val()
        ... 4
        >>> val = build_transform({'function': '[4, 5]'}, iter=False)
        >>> val()
        ... [4, 5]
    '''
    # Ensure that the transform is a dict with "function:" in it. (This is a common mistake)
    if not isinstance(conf, dict) or 'function' not in conf:
        raise ValueError(f'{filename}: needs "function:". Got {conf!r}')

    conf = {key: val for key, val in conf.items() if key in {'function', 'args', 'kwargs'}}

    # The returned function takes a single argument by default
    if vars is None:
        vars = {'_val': None}
    # Treat kwargs=True as kwargs=kwargs. It adds **kwargs to the function call
    if kwargs is True:
        kwargs = 'kwargs'

    # If the function is a list, treat it as a pipeline
    if isinstance(conf['function'], (list, tuple)):
        return build_pipeline(conf['function'], vars, kwargs, filename, cache, iter)

    # Get the name of the function in case it's specified as a function call
    # expr is the full function / expression, e.g. str("abc")
    # tree is the ast result
    expr = str(conf['function'])
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
    if module_name in vars or (isinstance(kwargs, str) and module_name == kwargs):
        expr = function_name
    # If it's a function call, construct the function signature
    elif function_name is not None:
        function = locate(function_name, modules=['gramex.transforms'])
        doc = function.__doc__
        if function is None:
            app_log.error(f'function:{filename}: Cannot load function {function_name}')
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
    signature = ', '.join('{:s}={!r:}'.format(k, v) for k, v in vars.items())
    if kwargs:
        signature += (', ' if signature else '') + f'**{kwargs}'
    body = [
        f'def transform({signature}):\n',
        f'\timport {modulestr}\n' if modulestr else '',
        f'\treload_module({modulestr})\n' if modulestr and not cache else '',
        f'\tresult = {expr}\n',
        # If the result is a generator object, return it. Else, create a list and
        # return that. This ensures that the returned value is always an iterable
        '\treturn result if isinstance(result, GeneratorType) else [result,]'
        if iter
        else '\treturn result',
    ]

    # Compile the function with context variables
    import gramex.transforms
    from gramex.cache import reload_module

    context = dict(
        reload_module=reload_module,
        GeneratorType=GeneratorType,
        Return=tornado.gen.Return,
        AttrDict=AttrDict,
        **{key: getattr(gramex.transforms, key) for key in gramex.transforms.__all__},
    )
    code = compile(''.join(body), filename=filename, mode='exec')
    # B102:exec_used is safe since the code is written by app developer
    exec(code, context)  # nosec B102

    # Return the transformed function
    result = context['transform']
    result.__name__ = str(function_name or filename)
    result.__doc__ = str(doc)
    result.__func__ = function

    return result


def build_pipeline(
    conf: dict,
    vars: dict = None,
    kwargs: Union[bool, str] = False,
    filename: str = 'pipeline',
    cache: bool = False,
    iter: bool = True,
):
    '''Converts an expression list into a callable function (called a pipeline).

    Examples:
        >>> fn = build_pipeline([
        ...     {'name': 'x', 'function': '1 + 2'},
        ...     {'name': 'y', 'function': '3 + 4'},
        ...     {'function': 'x + y'},
        ... ], iter=False)
        >>> fn()
        ... 10

    This compiles the expression list into a callable function roughty as follows:

    ```python
    def pipeline(_val):
        x = 1 + 2
        y = 3 + 4
        return x + y
    ```

    Parameters:
        conf: expression list to compile
        vars: variables passed to the compiled function
        kwargs: `True` to accept **kwargs. Any string to define the kwargs variable name
        filename: filename to print in case of errors
        cache: `False` re-imports modules if changed. `True` caches module
        iter: `True` always returns an iterable. `False` returns a single value

    `conf` is a **list** of the same `conf` that
    [build_transform][gramex.transforms.build_transform] accepts.

    Other parameters are the same as [build_transform][gramex.transforms.build_transform].
    '''
    if not isinstance(conf, (list, tuple)):
        raise ValueError(f'pipeline:{filename}: must be a list, not {type(conf)}')
    if len(conf) == 0:
        raise ValueError(f'pipeline:{filename}: cannot be an empty list')
    if vars is None:
        vars = {}
    if not isinstance(vars, dict):
        raise ValueError(f'pipeline:{filename}: vars must be a dict, not {type(vars)}')
    # current_scope has the variables available in each stage.
    # Whenever a stage defines a `name:`, add it to the current_scope.
    current_scope = dict(vars)
    n, compiled_stages = len(conf), []
    for index, spec in enumerate(conf, start=1):
        if not isinstance(spec, dict):
            spec = {'function': str(spec)}
        # Store the original configuration for reporting error messages
        stage = {'spec': spec, 'index': index}
        if 'function' not in spec:
            raise ValueError(f'pipeline:{filename}: {index}/{n}: missing "function"')
        # Compile the function, allowing use of all variables in current_scope
        stage['function'] = build_transform(
            {'function': spec['function']},
            vars=current_scope,
            kwargs=kwargs,
            filename=f'pipeline:{filename} {index}/{n}',
            cache=cache,
            iter=False,
        )
        # If the stage defines a name, add it as a variable for current_scope
        if 'name' in spec:
            current_scope[spec['name']] = None
        compiled_stages.append(stage)

    def run_pipeline(**kwargs):
        '''
        This returned function actually runs the pipeline.
        It loops through each pipeline step, runs the function, and returns the last value.

        Any `kwargs` passed are used as globals. (They default to the `vars` in build_pipeline.)

        If a step specifies a `name`, the result is stored in `kwargs[name]`,
        making it available as a global to the next step.

        Logs the time taken for each step (and errors, if any) in storelocations.pipeline.
        '''
        start = datetime.datetime.utcnow().isoformat()
        app_log.debug(f'pipeline:{filename} running')
        error, stage = '', {'spec': {}, 'index': None}
        try:
            # Use kwargs as globals for the steps. Initialize with vars
            merge(kwargs, vars, 'setdefault')
            result = None
            for stage in compiled_stages:
                result = stage['function'](**kwargs)
                # Store the returned value in the kwargs as globals
                if 'name' in stage['spec']:
                    kwargs[stage['spec']['name']] = result
            # If the pipeline SHOULD return an iterable, ensure last result is iterable
            if iter:
                return result if isinstance(result, GeneratorType) else [result]
            else:
                return result
        except Exception:
            # On any exception, capture the error and traceback to log it
            import sys
            import traceback

            error = f'pipeline:{filename} {stage["index"]}/{n} failed: {stage["spec"]}'
            error += '\n' + ''.join(traceback.format_exception(*sys.exc_info()))
            # but raise the original Exception
            raise
        finally:
            # Log pipeline execution (and error, if any)
            from gramex.services import info

            if 'pipeline' in info.storelocations:
                from gramex.data import insert

                end = datetime.datetime.utcnow().isoformat()
                insert(
                    **info.storelocations.pipeline,
                    id=['name', 'start'],
                    args={
                        'name': [filename],
                        'start': [start],
                        'end': [end],
                        'error': [error],
                    },
                )

    return run_pipeline


def condition(*args):
    '''
    !!! Deprecated
        Use the `if` construct in config keys instead.

    Variables can also be computed based on conditions:

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
    import warnings

    warnings.warn(
        'condition() deprecated. https://gramener.com/gramex/guide/config/#conditions',
        DeprecationWarning,
    )
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
            # B307:eval is safe here since `cond` is written by app developer
            if eval(Template(cond).substitute(var_defaults)):  # nosec B307
                return val
        elif cond:
            return val

    # If none of the conditions matched, we'll be here.
    # If there are an odd number of arguments and there's at least one condition,
    # treat the last as a default.
    if len(args) % 2 == 1 and len(args) > 2:
        return args[-1]


def flattener(fields: dict, default: Any = None, filename: str = 'flatten'):
    '''Generates a function that flattens deep dictionaries.

    Examples:

        >>> flat = flattener({
        ...     'id': 'id',
        ...     'name': 'user.screen_name'
        ... })
        >>> flat({'id': 1, 'user': {'screen_name': 'name'}})
        ... {'id': 1, 'name': 'name'}

    Parameters:
        fields: a mapping of keys to object paths
        default: the value to use if the object path is not found
        filename: filename to print in case of errors

    Object paths are dot-seperated, and constructed as follows:

    ```text
    '1'   => obj[1]
    'x'   => obj['x']
    'x.y' => obj['x']['y']
    '1.x' => obj[1]['x']
    ```
    '''
    body = [
        f'def {filename}(obj):\n',
        '\tr = AttrDict()\n',
    ]

    def assign(field, target, catch_errors=False):
        if catch_errors:
            body.append(f'\ttry: r[{field!r}] = {target}\n')
            body.append(f'\texcept (KeyError, TypeError, IndexError): r[{field!r}] = default\n')
        else:
            body.append(f'\tr[{field!r}] = {target}\n')

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
    # B307:eval is safe here since the code is constructed entirely in this function
    eval(code, context)  # nosec B307
    return context[filename]


_once_info = {}


def once(*args, **kwargs):
    '''Returns `False` if once() has been called before with these arguments. Else `True`.

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
        return method(args[-1] if args else param.default)


class Header(str):
    pass


def handler(func):
    """Wrap a function to make it compatible with a FunctionHandler.

    Use this decorator to expose a function as a REST API, with path or URL parameters mapped to
    function arguments with type conversion.

    Suppose you have the following function in `greet.py`:

    ```python
    @handler
    def birthday(name: str, age: int):
        return f'{name} turns {age:d} today! Happy Birthday!'
    ```

    Then, in `gramex.yaml`, you can use it as a FunctionHandler as follows::

    ```yaml
    url:
        pattern: /$YAMLURL/greet
        handler: FunctionHandler
        kwargs:
            function: greet.birthday
    ```

    Now, `/greet?name=Gramex&age=0010` returns "Gramex turns 10 today! Happy Birthday!".
    It converts the URL parameters into the types found in the annotations, e.g. `0010` into 10.

    An alternate way of configuring this is as follows::

        url:
            pattern: /$YAMLURL/greet/name/(.*)/age/(.*)
            handler: FunctionHandler
            kwargs:
                # You can pass name=... and age=... as default values
                # but ensure that handler is the first argument in the config.
                function: greet.birthday(handler, name='Name', age=10)

    Now, `/greet/name/Gramex/age/0010` returns "Gramex turns 10 today! Happy Birthday!".

    The function args and kwargs are taken from these sources this in order.

    1. From the YAML function
        - e.g. `function: greet.birthday('Name', age=10)` sets `name='Name'` and `age=10`
    2. Over-ridden by YAML URL pattern
        - e.g. `pattern: /$YAMLPATH/(.*)/(?P<age>.*)`
        - URL `/greet/Name/10` sets `name='Name'` and `age=10`
    3. Over-ridden by URL query parameters
        - e.g. URL `/greet?name=Name&age=10` sets `name='Name'` and `age=10`
    4. Over-ridden by URL POST body parameters
        - e.g. `curl -X POST /greet -d "?name=Name&age=10"` sets `name='Name'` and `age=10`

    `handler` is also available as a kwarg. You can use this as the last positional argument or
    a keyword argument. Both `def birthday(name, age, handler)` and
    `def birthday(name, age, handler=None)` are valid.
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


# Define direct keys. These can be used as-is
_transform_direct_vars = {
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
    # TODO: 'size': 'handler.get_content_size()' is not available in RequestHandler
    'user': '(handler.current_user or {}).get("id", "")',
    'session': 'handler.session.get("id", "")',
    'error': 'getattr(handler, "_exception", "")',
}

# Define object keys for us as key.value. E.g. cookies.sid, user.email, etc
_transform_obj_vars = {
    'args': 'handler.get_argument("{val}", "")',
    'request': 'getattr(handler.request, "{val}", "")',
    'headers': 'handler.request.headers.get("{val}", "")',
    'cookies': (
        'handler.request.cookies["{val}"].value ' + 'if "{val}" in handler.request.cookies else ""'
    ),
    'user': '(handler.current_user or {{}}).get("{val}", "")',
    'env': 'os.environ.get("{val}", "")',
}


def handler_expr(expr):
    if expr in _transform_direct_vars:
        return _transform_direct_vars[expr]
    if '.' in expr:
        prefix, value = expr.split('.', 2)
        if prefix in _transform_obj_vars:
            return _transform_obj_vars[prefix].format(val=value)
    raise ValueError(f'Unknown expression {expr}')


def build_log_info(keys: List, *vars: List):
    '''Utility to create logging values.

    Returns a function that accepts a handler and returns a dict of values to log.

    Examples:
        >>> log_info = build_log_info(['time', 'ip', 'cookies.sid', 'user.email'])
        >>> log_info(handler)
        ... {"time": 1655280440, "ip": "::1", "cookies.sid": "...", "user.email": "..."}

    Parameters:
        keys: list of keys to include in the log.
        *vars: additional variables to include in the log.

    `keys` can include: `name`, `class`, `time`, `datetime`, `method`, `uri`, `ip`, `status`,
    `duration`, port, `user`, `session`, `error`.

    It can also include:

    - `args.*`: value of the URL query parameter ?arg=
    - `request.*`: value of `handler.request.*`
    - `headers.*`: value of the HTTP header
    - `cookies.*`: value of the HTTP cookie
    - `user.*`: key in the user object
    - `env.*`: value of the environment variable

    `vars` can be any list of any variables. When you pass these to the function, they're added to
    the returned value as-is. (This is used internally in [gramex.handlers.AuthHandler.setup])

    Examples:
        >>> log_info = build_log_info(['time'], 'event')
        >>> log_info(handler, event='x')
        ... {"time": 1655280440, "event": "x"}
    '''
    from gramex import conf

    vals = []
    for key in keys:
        if key in vars:
            vals.append(f'"{key}": {key},')
            continue
        try:
            vals.append(f'"{key}": {handler_expr(key)},')
        except ValueError:
            app_log.error(f'Skipping unknown key {key}')
    code = compile(
        'def fn(handler, %s):\n\treturn {%s}' % (', '.join(vars), ' '.join(vals)),
        filename='log',
        mode='exec',
    )
    context = {'os': os, 'time': time, 'datetime': datetime, 'conf': conf, 'AttrDict': AttrDict}
    # B102:exec_used is safe here since the code is constructed entirely in this function
    exec(code, context)  # nosec B102
    return context['fn']
