import sys

builtin_module = 'builtins' if sys.version_info[0] == 3 else '__builtin__'


def python_name(name):
    'Return the Python object given a module.name or name'
    if not name:
        raise NameError('Empty Python object')
    if '.' in name:
        module_name, object_name = name.rsplit('.', 1)
    else:
        module_name = builtin_module
        object_name = name
    try:
        __import__(module_name)
    except ImportError:
        raise NameError('%s: no module %s' % (name, module_name))
    module = sys.modules[module_name]
    if not hasattr(module, object_name):
        raise NameError('%s: no object %s in %s' % (name, module_name, object_name))
    return getattr(module, object_name)
