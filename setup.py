#!/usr/bin/env python

# Require setuptools -- distutils does not support install_requires
from setuptools import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

setup(
    name='gramex',
    version='1.0.0',
    description="Gramex is a declarative data analytics and visualization platform",
    long_description=readme + '\n\n' + history,
    author="S Anand",
    author_email='s.anand@gramener.com',
    url='http://code.gramener.com/s.anand/gramex',
    packages=[
        'gramex',
    ],
    package_dir={'gramex':
                 'gramex'},
    include_package_data=True,
    install_requires=[
        # Abstract dependencies here, concrete dependencies in requirements.txt
        # See https://packaging.python.org/en/latest/requirements.html
        'pathlib',                  # Python 3.3+ already has it
        'orderedattrdict',          # OrderedDict with attr access
        'tornado >= 4.0',           # Web server
        'PyYAML',                   # Parse YAML fils
        'crontab',                  # Parse crontab entries
    ],
    license="Other/Proprietary License",
    zip_safe=False,
    keywords='gramex',
    entry_points={
        'console_scripts': ['gramex = gramex:run']
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=[
    ]
)
