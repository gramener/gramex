import os
import sys
import yaml
from fnmatch import fnmatch


def commandline():
    '''Run `secrets` on the command line to save specific environment variables in a file.

    Used in CI tools (e.g. Gitlab/Travis) to save env variables into `.secrets.yaml`. For example,
    to export `$HOME` and all variables starting with `$HOME` to `.secrets.yaml`, run:

    ```shell
    secrets HOME > .secrets.yaml            # export HOME=... to .secrets.yaml
    secrets HOME=/tmp > .secrets.yaml       # export $HOME. If $HOME is not defined, use /tmp
    secrets HOME 'GOOGLE*' > .secrets.yaml  # export $HOME and all vars starting with $GOOGLE
    ```
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
        print(yaml.dump(result, default_flow_style=False, sort_keys=False).strip())  # noqa
