#!/usr/bin/env python

# Require setuptools -- distutils does not support install_requires
from setuptools import setup
from pip.req import parse_requirements
from pip.download import PipSession
import gramex


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

install_requires = [str(entry.req) for entry in
                    parse_requirements('requirements.txt', session=PipSession())]

setup(
    name='gramex',
    version=gramex.__version__,
    description="Gramex is a declarative data analytics and visualization platform",
    long_description=readme + '\n\n' + history,
    author="Gramener",
    author_email='s.anand@gramener.com',
    url='http://code.gramener.com/s.anand/gramex',
    packages=[
        'gramex',
    ],
    package_dir={'gramex':
                 'gramex'},
    include_package_data=True,
    install_requires=install_requires,
    license="Other/Proprietary License",
    zip_safe=False,
    keywords='gramex',
    entry_points={
        'console_scripts': ['gramex = gramex:init']
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
        'markdown',
    ]
)
