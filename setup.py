from setuptools import setup, find_packages
from pathlib import Path

setup(
    name='gramex',
    version='1.85.0',
    description='Gramex: Low Code Data Solutions Platform',
    author='Gramener',
    author_email='s.anand@gramener.com',
    url='https://gramener.com/gramex/',
    download_url='https://github.com/gramener/gramex',
    license='MIT',
    keywords='gramex',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.7',
    long_description=(Path(__file__).parent / "README.md").read_text(),
    long_description_content_type='text/markdown',
    # Auto-detect, but ignore test packages (tests, testlib)
    packages=[pkg for pkg in find_packages() if not pkg.startswith('test')],
    # Read: http://stackoverflow.com/a/2969087/100904
    # package_data includes data files for binary & source distributions.
    # include_package_data is only for source distributions, uses MANIFEST.in.
    # We only use source distributions.
    include_package_data=True,
    # Libraries required for Gramex.
    # OPT: not required for startup, but for specific handlers / services
    # Keep in sync with guide/license/thirdparty.md
    install_requires=[
        'astor',  # for gramex.transforms.build_transform
        'cachetools>=3.0.0',  # for services.cache for memory cache
        'colorlog>=2.7.0',  # for Coloured log files
        'cron-descriptor',  # for gramex.apps.admin2.gramexadmin admin/schedule to pretty-print
        'crontab>=0.21',  # for services.schedule to parse crontab entries
        'diskcache>=2.8.3',  # for urlcache.DiskCache
        'h5py',  # for MLHandler saves .h5 files. TODO: Migrate away from .h5
        'joblib',  # for gramex.ml
        'lxml',  # for gramex.pptgen2
        'markdown',  # OPT: for transforms, gramex.services.create_alert()
        'matplotlib',  # OPT: for gramex.data.download() charts, scale.colors, pptgen2
        'numpy',  # for ml, topcause, pptgen
        'oauthlib>=1.1.2',  # for socialhandler, twitterstream
        'openpyxl',  # for gramex.cache.open .XLSX reading
        'orderedattrdict>=1.6.0',  # for OrderedDict with attr access for configs
        'packaging',  # for gramex.init() to parse gramex versions
        'pandas',  # for all data processing
        'pillow',  # for pptgen2
        'psutil',  # for gramexadmin to monitor process
        'python-dateutil',  # for gramex.config.CustomJSONEncoder, gramex.data._convertor
        # See https://github.com/scanny/python-pptx/issues/754
        'python-pptx>=0.6.6,<=0.6.19',  # for pptgen2
        'python-slugify',  # for Pre-defined slugs at gramex.config.slug
        'pyyaml>=5.1',  # for Parse YAML files for config
        'redis>=2.10.0',  # for RedisStore
        'requests',  # for all HTTP requests
        'scikit-learn',  # For MLHandler, gramex.ml. TODO: version >=0.23.2,<1.0
        'seaborn',  # OPT: gramex.data.download()
        'six',  # for Python 3 compatibility. TODO: Avoid this
        'sqlalchemy',  # for gramex.data.filter()
        'sqlitedict>=1.5.0',  # for SQLiteStore
        'tables',  # for HDF5 reading / writing. TODO: Where do we need this?
        'tornado>=5.1.1',  # for Web server
        'typing_extensions',  # for future-proof typing
        'tzlocal',  # for gramex.data influxdb. TODO: Use dateutil.tz.tzlocal()
        'watchdog',  # for Monitor file changes
    ],
    extras_require={
        # pip install 'gramex[full]' for better debugging and ML support
        'full': [
            'boto3',  # for gramex.services.sns.AmazonSNS
            'datasets',  # for gramex.transformers
            'ipdb',  # for better debugging
            'line_profiler',  # for gramex.debug.lineprofile
            'pymysql',  # for MySQL connections
            'scipy',  # for gramex.topcause
            'spacy',  # for gramex.transformers
            'statsmodels',  # for gramex.ml_api
            'transformers',  # for gramex.transformers
            'xlrd',  # for gramex.cache.open .XLS support (not .xlsx)
            # 'conda',  # not required except for rpy2 or reporting conda version
            # 'rpy2',  # deprecated
        ],
        'influxdb': ['influxdb_client'],
        'mongodb': [
            'pymongo',
            'bson',
        ],
        'servicenow': [
            'pysnow',
        ],
        'win32': [
            'pywin32',
        ],
        'lint': [
            'bandit',
            'black',
            'flake8',
            'flake8-2020',
            'flake8-blind-except',
            'flake8-debugger',
            'flake8-print',
            'pep8-naming',
        ],
        'doc': [
            'mkdocs',
            'mkdocstrings',
            'mkdocstrings[python]',
        ],
        'test': [
            'boto3',  # for gramex.services.sns.AmazonSNS testing
            'coverage',  # for code coverage
            'cssselect',  # for tests.check_css() in test_admin, test_auth, test_alerts
            'datasets',  # for gramex.transformers
            'elasticsearch7',  # for gramexlog: features
            'gramexenterprise',  # for auth testing
            'nose',  # for all test cases
            'pdfminer.six',  # for test_capturehandler
            'psycopg2 >= 2.7.1',  # for PostgreSQL tests
            'pymongo',  # for MongoDB tests
            'pymysql',  # for MySQL tests
            'scipy',  # for gramex.topcause
            'spacy',  # for gramex.transformers
            'statsmodels',  # for gramex.ml_api
            'testfixtures',  # For logcapture
            'transformers',  # for gramex.transformers
            'websocket-client',  # For test_websockethandler
        ],
    },
    # Command-line scripts provided by Gramex
    entry_points={
        'console_scripts': [
            'gramex = gramex:commandline',
            'secrets = gramex.secrets:commandline',
            'slidesense = gramex.pptgen2:commandline',
        ]
    },
)
