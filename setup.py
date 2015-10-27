#!/usr/bin/env python

# Require setuptools -- distutils does not support install_requires
from setuptools import setup, find_packages
from pip.req import parse_requirements
from pip.download import PipSession
import os
import json

setup(
    long_description=(open('README.rst').read() + '\n\n' +
                      open('HISTORY.rst').read().replace('.. :changelog:', '')),
    packages=find_packages(),

    # Read: http://stackoverflow.com/a/2969087/100904
    # package_data includes data files for binary & source distributions
    # include_package_data is only for source distributions, uses MANIFEST.in
    package_data={
        'gramex': [
            os.path.join(dirpath, filename).lstrip('gramex/')
            for dirpath, dirnames, filenames in os.walk('gramex/lib')
            for filename in filenames
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

    # release.json contains name, description, version, etc
    **json.load(open('gramex/release.json'))
)
