# Set the environment variable PYTHON to your custom Python exe
PYTHON ?= python
# This is the location where releases are uploaded to
UPLOAD = ubuntu@gramener.com:/mnt/gramener/downloads/release/

.PHONY: clean-pyc clean-build docs clean

BROWSER := $(PYTHON) -c "import os, sys; os.startfile(os.path.abspath(sys.argv[1]))"

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

lint:
	flake8 gramex tests

test:
	$(PYTHON) setup.py test

test-all:
	tox

coverage:
	$(PYTHON) -m coverage run --include='gramex*' setup.py test
	$(PYTHON) -m coverage report -m
	$(PYTHON) -m coverage html
	$(BROWSER) htmlcov/index.html

PDFLATEX := $(shell pdflatex -version 2>/dev/null)
docs:
	rm -f docs/gramex.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ gramex
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
ifdef PDFLATEX
	$(MAKE) -C docs latexpdf
else
	@echo "No pdflatex found. Install pdflatex to build PDF docs"
endif

showdocs:
	$(BROWSER) docs/_build/html/index.html

release-test: clean-test lint docs test coverage

release: clean
	$(PYTHON) setup.py sdist
	$(PYTHON) setup.py bdist_wheel
	rsync -avzP dist/* $(UPLOAD)

dist: clean
	$(PYTHON) setup.py sdist
	$(PYTHON) setup.py bdist_wheel
	ls -l dist

install: clean
	$(PYTHON) setup.py install
