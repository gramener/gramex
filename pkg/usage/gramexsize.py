'''Saves cyclomatic complexity of Gramex code and corresponding YAML config.'''
import ast
import logging
import mccabe
import os
import sys
from collections import Counter
from fnmatch import fnmatch
from typing import Iterator

folder = os.path.dirname(os.path.abspath(__file__))


def complexity(dir: str) -> Iterator[dict]:
    '''Yield cyclomatic complexity of each function in a folder.

    Examples:
        >>> for item in complexity('myproject/'):
        ...     print(item['module'], item['entity'], item['complexity'])

    Parameters:
        dir: path to folder to locate .py files in

    It returns an iterator of dictionaries with keys:

    - `source`: Path to `.py` file relative to `dir`, e.g. `pkg/module.py`
    - `module`: `path` converted to module name, `e.g. `pkg.module`
    - `entity`: function or method, e.g. `ClassName.method_name`. For code outside functions,
        this is `If`, `TryExcept`, `With`, `Loop`, or "Stmt".
    - `lineno`: line at which `entity` appears in `source`
    - `column`: column at which `entity` appears in `source`
    - `complexity`: McCabe (cyclomatic) complexity of the `entity`
    '''
    for root, _dirs, files in os.walk(dir):
        for file in files:
            if file.lower().endswith('.py'):
                path: str = os.path.join(root, file)
                rel_path: str = os.path.relpath(path, dir)
                with open(path, 'rb') as handle:
                    code = handle.read()
                tree = compile(code, rel_path, 'exec', ast.PyCF_ONLY_AST)
                visitor = mccabe.PathGraphingAstVisitor()
                visitor.preorder(tree, visitor)
                for node in visitor.graphs.values():
                    yield {
                        'source': rel_path,
                        'module': rel_path[:-3].replace(os.sep, '.'),
                        'entity': node.entity,
                        'lineno': node.lineno,
                        'column': node.column,
                        'complexity': node.complexity(),
                    }


def gramexsize(*dirs: str):
    '''Saves complexity of Gramex code and corresponding YAML config in target.

    Examples:

        >>> gramexsize('/path/to/gramex/', '/path/to/gramexenterprise/', target='codesize.csv')
    '''
    import yaml
    import pandas as pd

    conf_file = os.path.join(folder, 'gramexsize.yaml')
    with open(conf_file) as handle:
        conf = yaml.safe_load(handle)

    total = Counter()
    for dir in dirs:
        for node in complexity(os.path.abspath(dir)):
            key = f"{node['module']}.{node['entity']}"
            for codepath, yamlpaths in conf['code2yaml'].items():
                if fnmatch(key, codepath):
                    yamlpaths = yamlpaths if isinstance(yamlpaths, list) else [yamlpaths]
                    for yamlpath in yamlpaths:
                        total[codepath, yamlpath] += node['complexity']
                    break
            else:
                logging.warning(f'Unmatched {key}')

    result = pd.Series(total).reset_index()
    result.columns = ['codepath', 'yamlpath', 'complexity']
    result.dropna(subset=['yamlpath']).to_csv(sys.stdout, index=False, lineterminator='\n')


if __name__ == '__main__':
    gramexsize(*sys.argv[1:])
