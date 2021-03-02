# Require setuptools -- distutils does not support install_requires
from setuptools import setup, find_packages
from fnmatch import fnmatch
from io import open
import json
import os


def read_gitignore(path, exclude=set()):
    '''
    Read .gitignore paths as an iterable of patterns, unless it is in the exclude set
    '''
    with open(path, encoding='utf-8') as handle:
        for line in handle.readlines():
            line = line.strip()
            if line and not line.startswith('#') and line not in exclude:
                yield line


def recursive_include(root, path, ignores=[], allows=[]):
    '''Go to root dir and yield all files under path that are in allows, not in ignores'''
    # Change to root directory
    cwd = os.getcwd()
    os.chdir(root)
    for root, dirs, files in os.walk(path):
        # Do not parse directories that are in .gitignore
        for index in range(len(dirs) - 1, 0, -1):
            name = dirs[index]
            for pattern in ignores:
                if fnmatch(name, pattern):
                    del dirs[index]
        # Yield all files that are not in .gitignore
        for name in files:
            target = os.path.join(root, name)
            ignore = False
            for pattern in ignores:
                if fnmatch(name, pattern) or fnmatch(target, pattern):
                    ignore = True
                    break
            if len(allows) > 0:
                for pattern in allows:
                    if not fnmatch(name, pattern) or not fnmatch(target, pattern):
                        ignore = True
                        break
            if not ignore:
                yield target
    # Change back to original directory
    os.chdir(cwd)


ignore_patterns = list(read_gitignore('.gitignore', exclude={'node_modules'}))

with open('README.rst', encoding='utf-8') as handle:
    long_description = handle.read() + '\n\n'

# release.json contains release info (name, description, version), packages to install, etc
with open('gramex/release.json', encoding='utf-8') as handle:
    release = json.load(handle)

# Add a matching line in MANIFEST.in
# Add a matching list in testlib/test_setup.py for verification
gramex_files = [
    'gramex.yaml',
    'deploy.yaml',
    'apps.yaml',
    'favicon.ico',
    'release.json',
    'download.vega.js',
    'pptgen2/config.yaml',
]
gramex_files += list(recursive_include('gramex', 'handlers', ignore_patterns, ['*.html']))
gramex_files += list(recursive_include('gramex', 'pptgen', ignore_patterns, ['*.json']))
gramex_files += list(recursive_include('gramex', 'apps', ignore_patterns))

setup(
    python_requires='~=3.7',
    long_description=long_description,
    # Auto-detect, but ignore test packages (tests, testlib)
    packages=[pkg for pkg in find_packages() if not pkg.startswith('test')],

    # Read: http://stackoverflow.com/a/2969087/100904
    # package_data includes data files for binary & source distributions
    # include_package_data is only for source distributions, uses MANIFEST.in
    package_data={
        'gramex': gramex_files,
    },
    include_package_data=True,
    # Pick up dependencies from gramex/release.json
    # To ensure that pip install works, only include packages that work via pip (not conda)
    install_requires=[req for part in ('lib', 'pip') for req in release[part]],
    zip_safe=False,
    entry_points={
        'console_scripts': release['console'],
        'pytest11': ['gramextest = gramex.gramextest']
    },
    test_suite='tests',
    # NOTE: Don't use tests_require. setup.py can't install nose plugins like coverage.
    # Use `make test-setup` to install rest requirements from tests/requirements.txt.
    **release['info']
)
