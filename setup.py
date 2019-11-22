# Require setuptools -- distutils does not support install_requires
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools import setup, find_packages
from fnmatch import fnmatch
from io import open
import logging
import json
import os

# Libraries required for Gramex
# Keep this in sync with guide/license/thirdparty.md
# REQ: required packages for Gramex
# OPT: optional packages not required for startup, but "batteries included"
# (conda): packages is part of Anaconda, not Miniconda
install_requires = [
    # Requires conda install
    # 'line_profiler',                # OPT: (conda) For gramex.debug
    # 'rpy2',                         # OPT: (conda) For gramex.ml.r()
    # 'sklearn',                      # OPT: (conda) For gramex.ml
    'argh >= 0.24.1',               # REQ: dependency for watchdog
    'boto3 >= 1.5',                 # SRV: Amazon services
    'cachetools >= 3.0.0',          # SRV: services.cache for memory cache
    'colorama',                     # REQ: (conda) gramex.init()
    'colorlog >= 2.7.0',            # REQ: Coloured log files
    'cron-descriptor',              # OPT: admin/schedule to pretty-print cron
    'crontab >= 0.21',              # SRV: services.schedule to parse crontab entries
    'cssselect',                    # OPT: pytest gramex plugin
    'diskcache >= 2.8.3',           # SRV: services.cache for disk cache
    'h5py',                         # OPT: (conda) gramex.cache.HDF5Store
    'ipdb',                         # OPT: gramex.debug
    'inflect',                      # REQ: NLG
    'jmespath',                     # OPT: pytest gramex plugin
    'joblib',                       # OPT: For gramex.ml
    'ldap3 >= 2.2.4',               # OPT: LDAP connections
    'lxml',                         # OPT: (conda) gramex.pptgen
    'markdown',                     # OPT: transforms, gramex.services.create_alert()
    'matplotlib',                   # OPT: (conda) gramex.data.download()
    'oauthlib >= 1.1.2',            # SRV: OAuth request-signing
    'orderedattrdict >= 1.4.3',     # REQ: OrderedDict with attr access for configs
    'pandas',                       # REQ: (conda) gramex.data.filter()
    'passlib >= 1.6.5',             # REQ: password storage (e.g. in handlers.DBAuth)
    'pathlib',                      # REQ: Manipulate paths. Part of Python 3.3+
    'pathtools >= 0.1.1',           # REQ: dependency for watchdog
    'psutil',                       # REQ: monitor process
    'pymysql',                      # OPT: MySQL connections
    'pytest',                       # OPT: (conda) pytest gramex plugin
    'python-pptx >= 0.6.6',         # SRV: pptgen
    'pyyaml >= 5.1',                # REQ: Parse YAML files for config
    'redis >= 2.10.0',              # SRV: RedisStore
    'requests',                     # REQ: HTTP library for python
    'seaborn',                      # OPT: (conda) gramex.data.download()
    'selenium',                     # OPT: pytest gramex plugin
    'setuptools >= 16.0',           # REQ: 16.0 has good error message support
    'shutilwhich >= 1.1.0',         # REQ: shutil.which backport
    'six',                          # REQ: Python 3 compatibility
    'sqlalchemy',                   # REQ: (conda) gramex.data.filter()
    'sqlitedict >= 1.5.0',          # SRV: SQLiteStore
    'tables',                       # REQ: HDF5 reading / writing
    'textblob',                     # OPT: Gramex Guide TwitterRESTHandler example
    'tornado == 5.1.1',             # REQ: Web server
    'watchdog >= 0.8',              # REQ: Monitor file changes
    'xlrd',                         # REQ: (conda) gramex.data.download()
    'xmljson >= 0.1.5',             # SRV: transforms.badgerfish to convert objects to/from XML
]


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


def install_apps(self):
    logging.basicConfig(level=logging.INFO)
    try:
        import gramex.install
    except Exception:
        logging.error('Run gramex setup --all to install apps')
        return
    # Guess the installation directory
    if hasattr(self, 'installed_projects') and 'gramex' in self.installed_projects:
        install_dir = self.installed_projects['gramex'].location
    elif hasattr(self, 'install_lib'):
        install_dir = self.install_lib
    elif hasattr(self, 'install_dir'):
        install_dir = self.install_dir
    else:
        logging.error('Run gramex setup --all to install apps')
        return
    # Install the gramex apps
    root = os.path.join(os.path.abspath(install_dir), 'gramex', 'apps')
    logging.info('Setting up Gramex apps at %s', root)
    for filename in os.listdir(root):
        target = os.path.join(root, filename)
        if os.path.isdir(target):
            try:
                gramex.install.run_setup(target)
            except Exception:
                logging.exception('Installation failed: %s', target)
    # Install guide
    gramex.install.install(['guide'], {})


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        develop.run(self)
        install_apps(self)


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        install_apps(self)


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
    'favicon.ico',
    'release.json',
    'download.vega.js',
]
gramex_files += list(recursive_include('gramex', 'handlers', ignore_patterns, ['*.html']))
gramex_files += list(recursive_include('gramex', 'pptgen', ignore_patterns, ['*.json']))
gramex_files += list(recursive_include('gramex', 'apps', ignore_patterns))

setup(
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
    install_requires=install_requires,
    zip_safe=False,
    entry_points={
        'console_scripts': ['gramex = gramex:commandline'],
        'pytest11': ['gramextest = gramex.gramextest']
    },
    test_suite='tests',
    tests_require=[
        'nose',
        'coverage',
        'python-dateutil',          # For schedule testing
        'testfixtures',             # For logcapture
        'sphinx_rtd_theme',         # For documentation
        'websocket-client',         # For websocket testing
        'pdfminer.six',             # For CaptureHandler testing
        'cssselect',                # For HTML testing (test_admin.py)
        'psycopg2 >= 2.7.1'         # OPT: PostgreSQL connections
    ],
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
    **release_args
)
