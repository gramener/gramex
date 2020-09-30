import os
import sys
import yaml
from fnmatch import fnmatch


def commandline():
    '''
    Running ``secrets KEY1 KEY_* KEY=VALUE`` saves specified environment variables in a file.
    Use in CI tools (e.g. Gitlab/Travis) to save env variables in ``.secrets.yaml``.

    Example::

        secrets GOOGLE_* *SECRET* > .secrets.yaml
    '''
    result = {}
    for pattern in sys.argv[1:]:
        if '=' in pattern:
            key, val = pattern.split('=', 1)
            result[key] = val
        else:
            for key, val in os.environ.items():
                if fnmatch(key, pattern):
                    result[key] = val
    if result:
        print(yaml.dump(result, default_flow_style=False, sort_keys=False).strip())     # noqa
