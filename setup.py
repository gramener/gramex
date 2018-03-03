# Require setuptools -- distutils does not support install_requires
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools import setup, find_packages
from pip.req import parse_requirements
from pip.download import PipSession
from distutils import log
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


ignore_patterns = list(read_gitignore('.gitignore', exclude={'node_modules'}))


def install_apps(warn):
    import gramex.install
    root = 'gramex/apps/'
    for filename in os.listdir(root):
        target = os.path.join(root, filename)
        if os.path.isdir(target):
            log.info('Installing %s. This may take time...', filename)
            gramex.install.run_setup(target)


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        install_apps(self.warn)
        develop.run(self)


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install_apps(self.warn)
        install.run(self)


def recursive_include(root, path, ignores=[], allows=[]):
    '''Go to root dir and yield all files under path that'''
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


with open('README.rst', encoding='utf-8') as handle:
    long_description = handle.read() + '\n\n'

# release.json contains name, description, version, etc
with open('gramex/release.json', encoding='utf-8') as handle:
    release_args = json.load(handle)

# Add a matching line in MANIFEST.in
# Add a matching list in testlib/test_setup.py for verification
gramex_files = [
    'gramex.yaml',
    'deploy.yaml',
    'apps.yaml',
    'release.json',
]
gramex_files += list(recursive_include('gramex', 'handlers', ignore_patterns, ['*.html']))
gramex_files += list(recursive_include('gramex', 'pptgen', ignore_patterns, ['*.json']))
gramex_files += list(recursive_include('gramex', 'apps', ignore_patterns))

setup(
    long_description=long_description,
    packages=find_packages(),

    # Read: http://stackoverflow.com/a/2969087/100904
    # package_data includes data files for binary & source distributions
    # include_package_data is only for source distributions, uses MANIFEST.in
    package_data={
        'gramex': gramex_files,
    },
    include_package_data=True,
    install_requires=[
        str(entry.req)
        for entry in parse_requirements('requirements.txt', session=PipSession())
        if entry.match_markers()
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': ['gramex = gramex:commandline']
    },
    test_suite='tests',
    tests_require=[
        'nose',
        'coverage',
        'testfixtures',             # For logcapture
        'sphinx_rtd_theme',         # For documentation
        'websocket-client',         # For websocket testing
        'pdfminer.six',             # For CaptureHandler testing
        'bandit',                   # For security testing
    ],
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
    **release_args
)
