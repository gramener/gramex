import six
from collections import OrderedDict
from gramex.config import recursive_encode
from six.moves.urllib_parse import urlparse, parse_qsl, urlencode


SET, ADD, POP, XOR = object(), object(), object(), object()


class URLUpdate(object):
    '''
    u(ADD, key, val, POP, key, SET, key, val, XOR, key)
    '''
    cmds = {SET, ADD, POP, XOR}

    def __init__(self, url):
        self.url = urlparse(url)
        self.args = OrderedDict()
        for key, val in parse_qsl(self.url.query, keep_blank_values=True):
            self.args.setdefault(key, []).append(val)
        self.cache = {}

    def __call__(self, *cmds):
        _key, cmds = cmds, list(cmds)
        if _key not in self.cache:
            # deepcopy of args preserving order
            args = OrderedDict((k, list(v)) for k, v in self.args.items())
            while len(cmds):
                cmd = cmds.pop(0)
                if cmd == ADD:
                    key, val = cmds.pop(0), cmds.pop(0)
                    if key not in args:
                        args[key] = [val]
                    elif val not in args[key]:
                        args[key].append(val)
                elif cmd == SET:
                    key, val = cmds.pop(0), cmds.pop(0)
                    if val is None:
                        args.pop(key, None)
                    else:
                        args[key] = [val]
                elif cmd == POP:
                    key = cmds.pop(0)
                    val = cmds.pop(0) if len(cmds) and cmds[0] not in self.cmds else None
                    if key in args:
                        if val is None:
                            args.pop(key)
                        elif val in args[key]:
                            args[key].remove(val)
                elif cmd == XOR:
                    key, val = cmds.pop(0), cmds.pop(0)
                    if key in args:
                        if val in args[key]:
                            args[key].remove(val)
                        else:
                            args[key].append(val)
                    else:
                        args[key] = [val]
            if six.PY2:
                recursive_encode(args)
            self.cache[_key] = urlencode(args, doseq=True)
        return self.cache[_key]
