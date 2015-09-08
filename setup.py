#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    # TODO: put package requirements here
]

test_requirements = [
    # TODO: put package test requirements here
]

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
    install_requires=requirements,
    license="Other/Proprietary License",
    zip_safe=False,
    keywords='gramex',
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
    tests_require=test_requirements
)
