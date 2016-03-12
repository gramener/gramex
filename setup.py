#!/usr/bin/env python

# Require setuptools -- distutils does not support install_requires
from setuptools import setup, find_packages
from pip.req import parse_requirements
from pip.download import PipSession
from io import open
import os
import json

with open('README.rst', encoding='utf-8') as handle:
    long_description = handle.read() + '\n\n'

with open('HISTORY.rst', encoding='utf-8') as handle:
    long_description += handle.read().replace('.. :changelog:', '')

# release.json contains name, description, version, etc
with open('gramex/release.json', encoding='utf-8') as handle:
    release_args = json.load(handle)

setup(
    long_description=long_description,
    packages=find_packages(),

    # Read: http://stackoverflow.com/a/2969087/100904
    # package_data includes data files for binary & source distributions
    # include_package_data is only for source distributions, uses MANIFEST.in
    package_data={
        'gramex': [
            os.path.join(dirpath, filename).lstrip('gramex/')
            for dirpath, dirnames, filenames in os.walk('gramex/lib')
            for filename in filenames
            # Skip vega-lite file that has a $ in the filename.
            if '$' not in filename
        ] + ['gramex.yaml', 'release.json']
    },
    include_package_data=True,

    install_requires=[str(entry.req) for entry in
                      parse_requirements('requirements.txt', session=PipSession())],
    zip_safe=False,
    entry_points={
        'console_scripts': ['gramex = gramex:init']
    },
    test_suite='tests',
    tests_require=[
        'markdown',
    ],
    **release_args
)
