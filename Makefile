# Set the environment variable PYTHON to your custom Python exe
PYTHON ?= python

.PHONY: clean-pyc clean-build docs clean

BROWSER := $(PYTHON) -c "import os, sys; os.startfile(os.path.abspath(sys.argv[1]))"

help:
	@echo "test - run tests quickly with the default Python"
	@echo "release-test - all tests required for release (lint, docs, coverage)"
	@echo "push-pypi - upload package to pypi"
	@echo "stats - show code stats"
	@echo "push-docs - upload documentation to gramener.com"
	@echo "lint - check style with flake8, eclint, eslint, htmllint, bandit"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "conda - create conda package"
	@echo "release - package and upload a release"
	@echo "dist - package"
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	rm -rf tests/uploads/
	rm -rf gramex-1.*
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -f .coverage
	rm -fr tests/htmlcov/
	rm -fr tests/.cache-url

lint:
	# Install packages using yarn (faster than npm)
	command -v yarn >/dev/null 2>&1 || npm install -g yarn
	command -v eclint 2>/dev/null 2>&1 || yarn global add eclint eslint htmllint-cli
	# eclint check files, ignoring node_modules
	find . -type f \( -name "*.html" -o -name "*.js" -o -name "*.css" -o -name "*.yaml" -o -name "*.md" \) ! -path '*/node_modules/*' ! -path '*/_build/*' ! -path '*/htmlcov/*' ! -path '*/.eggs/*' -print0 | xargs -0 eclint check
	# eslint requires eslint-plugin-* which are in package.json. yarn install them first
	yarn install
	eslint --ext js,html gramex/apps
	# htmllint: ignore test coverage, node_modules, Sphinx doc _builds, forms/ (TODO: FIX)
	find . -name '*.html' | grep -v htmlcov | grep -v node_modules | grep -v _build | grep -v forms/ | xargs htmllint
	# Run Python flake8 and bandit security checks
	command -v flake8 2>/dev/null 2>&1 || $(PYTHON) -m pip install flake8 pep8-naming flake8-gramex flake8-blind-except flake8-print flake8-debugger
	flake8 gramex testlib tests
	command -v bandit 2>/dev/null 2>&1 || $(PYTHON) -m pip install bandit
	bandit gramex --recursive --format csv || true    # Just run bandit as a warning

test-setup:
	$(PYTHON) -m pip install -r tests/requirements.txt

test: test-setup
	# Use python setup.py nosetests to ensure the correct Python runs.
	# (Note: Dependencies are set up via test-setup. setup.py does not have any tests_require.)
	$(PYTHON) setup.py nosetests

conda:
	# conda install conda-build
	conda build purge
	pip install orderedattrdict tornado==5.1.1
	python pkg/conda/conda-setup.py
	conda build -c conda-forge pkg/conda/

push-docker:
	$(PYTHON) -m pip install docker
	$(PYTHON) pkg/docker-py3/build.py
	docker login                # log in as sanand0 / pratapvardhan
	docker push gramener/gramex

release-test: clean-test lint docs test

docs:
	rm -f docs/gramex* docs/modules.rst
	sphinx-apidoc -o docs/ gramex --no-toc
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

release: clean
	$(PYTHON) setup.py sdist
	$(PYTHON) setup.py bdist_wheel

dist: clean release
	ls -l dist

stats:
	@echo python
	@find gramex -path '*node_modules/*' -prune -o -name '*.py' | grep '\.py$$' | xargs wc -l | tail -1
	@echo python setup
	@wc -l docs/conf.py setup.py | tail -1
	@echo javascript
	@find gramex -path '*node_modules/*' -prune -o -name '*.js' | grep '\.js$$' | grep -v node_modules | xargs wc -l | tail -1
	@echo tests
	@find tests testlib -path '*node_modules/*' -prune -o -name '*.py' | grep '\.py$$' | xargs wc -l | tail -1

push-docs: docs
	rsync -avzP docs/_build/html/ ubuntu@gramener.com:/mnt/gramener/learn.gramener.com/gramex/

push-pypi: clean
	python setup.py sdist
	# Note: if this fails, add '-p PASSWORD'
	twine upload -u gramener dist/*

# Gramex test coverage is part of Travis, and no longer needs to be deployed on gramener.com
# push-coverage:
# 	rsync -avzP tests/htmlcov/ ubuntu@gramener.com:/mnt/gramener/demo.gramener.com/gramextestcoverage/
