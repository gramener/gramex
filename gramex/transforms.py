'Functions to process functions'

import six
import yaml
import xmljson
import lxml.html
from .config import walk, load_imports
from pydoc import locate
from orderedattrdict.yamlutils import AttrDictYAMLLoader


def build_transform(conf, vars=[], args=None):
    '''
    Builds a new function based on a configuration object. For example::

        fn = build_transform({
            'function': 'json.dumps',
            'kwargs': {
                'separators': [',', ':']
            }
        })

    ... makes  ``fn(content)`` the same as ``json.dumps(content, separators=[',', ':'])``.

    The first parameter ``conf`` is a configuration dictionary with three keys:

    function
        name of a Python function to call. Defaults to ``lambda x: x``.
    args
        positional arguments to pass to the function. Defaults to ``['_content']``
    kwargs
        keywords arguments to pass to the function. Defaults to ``{}``

    If no ``function`` is provided, the result returns its input arguments as-is::

        >>> identity = build_transform({})
        >>> identity('x') == 'x'

    Any ``args`` are passed directly to the function. These are used as-is::

        >>> join = build_transform({'function': 'str.join', 'args': [',', ['a', 'b']]})
        >>> join('anything') == 'a,b'

    When calling the returned function, you can pass arguments. Defines these as
    ``vars``. For example, if you want to call ``join(string_list)``, then
    define ``vars=['string_list']``. Thereafter, any value of ``'string_list'``
    in ``args`` or ``kwargs`` is replaced with the ``string_list`` value you
    pass to ``join(string_list)``. For example::

        >>> join = build_transform({
        ...     'function': 'str.join',
        ...     'args': ['|', 'string_list']},
        ...     vars=['string_list'])
        >>> join(string_list=['a', 'b', 'c']) == 'a|b|c'

    You can pass multiple arguments this way. For example::

        >>> join = build_transform({
        ...     'function': 'str.join',
        ...     'args': ['separator', 'string_list']},
        ...     vars=['separator', 'string_list'])
        >>> join(string_list=['a', 'b', 'c'], separator=',') == 'a,b,c'

    By default, whatever you provide as ``vars`` is used in the configuration
    ``args`` in the same order. So the above is identical to this::

        >>> join = build_transform({'function': 'str.join'}, vars=['sep', 'str'])
        >>> join(',', ['a', 'b', 'c']) == 'a,b,c'

    Not all ``vars`` need to be used by the function. For example, though
    ``sep=`` is passed below, it is ignored::

        >>> join = build_transform({
        ...     'function': 'str.join',
        ...     'args': [',', 'list']},
        ...     vars=['sep', 'list'])
        >>> join(sep='anything', list=['a', 'b', 'c']) == 'a,b,c'
    '''
    # If vars is provided as a string, convert it to a list of string
    if not vars:
        vars = ['_content']
    vars = [vars] if isinstance(vars, six.string_types) else [str(x) for x in vars]

    # Use conf['args'] if available, ensuring that it's a string. Default to vars
    if 'args' in conf:
        args = conf['args']
        args = [args] if isinstance(args, six.string_types) else list(args)
    elif args is None:
        args = vars

    # kwargs defaults to a dict
    kwargs = dict(conf.get('kwargs', {}))

    # We create a Python string that contains the function. This is to speed
    # things up by pre-compiling and avoiding if conditions.
    result = ['def transform(' + ', '.join(vars) + '):']

    # Replace any vars in args with the variable
    for index, arg in enumerate(args):
        if arg in vars:
            result.append('\targs[%d] = %s' % (index, arg))

    # Replace any vars in kwargs with the variable
    for key, arg in kwargs.items():
        if arg in vars:
            result.append('\tkwargs[%s] = %s' % (repr(key), arg))

    # If no function is defined, use the identity function. Else, compile it
    # in the global context
    if 'function' not in conf:
        result.append('\treturn ' + ', '.join(args))
        doc = 'Return arguments as-is'
        name = 'identity'
        function = None
    else:
        result.append('\treturn function(*args, **kwargs)')
        function = locate(conf['function'])
        if function is None:
            raise NameError('Cannot find function %s' % conf['function'])
        doc = conf['function'].__doc__
        name = conf['function']

    # Compile the function
    context = {'args': args, 'kwargs': kwargs, 'function': function}
    exec('\n'.join(result), context)

    function = context['transform']
    function.__name__ = name
    function.__doc__ = doc
    return function


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
            node[tag] = maps[tag](value)
    return lxml.html.tostring(xmljson.badgerfish.etree(data)[0],
                              doctype=doctype, encoding='unicode')
