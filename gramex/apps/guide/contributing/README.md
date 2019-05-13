---
title: Contributing to Gramex
prefix: Contributing
...

[TOC]

## Set up Gramex

- The [master branch](http://github.com/gramener/gramex/tree/master/)
  holds the latest stable version.
- The [dev branch](http://github.com/gramener/gramex/tree/dev/) has the
  latest development version
- All other branches are temporary feature branches

Gramex can be developed on Python 2.7 and 3.6 on Windows or Linux.
To set up the development environment:

1. Download and install [Anaconda 5.0](http://continuum.io/downloads) or later
2. Install databases. Install PostgreSQL and MySQL. On Linux, this works:

```bash
sudo apt-get install -y git make sqlite3 postgresql postgresql-contrib libpq-dev python-dev
DEBIAN_FRONTEND=noninteractive apt-get -y -q install mysql-server
```

Clone and install the [dev branch](http://github.com/gramener/gramex/tree/dev/).

```bash
git clone git@code.gramener.com:cto/gramex.git
cd gramex
git checkout dev
pip install -e .
```

## Test Gramex

Gramex uses [nosetests](https://nose.readthedocs.io/en/latest/) for unit tests.
The tests are in 2 folders:

- [testlib/](https://github.com/gramener/gramex/tree/master/testlib/)
  has library tests that can run without starting Gramex.
- [tests/](https://github.com/gramener/gramex/tree/master/tests/)
  has URL-based tests that run after starting the Gramex server.

To run the tests, just run `python setup.py nosetests` for the first time.
Thereafter, you can run `nosetests`.

The tests take a long time. To test a subset, use `nosetests tests.<module>:<ClassName>.<method>`. For example:

```bash
nosetests testlib                           # Only test the libraries
nosetests testlib.test_data                 # Only run testlib/test_data.py
nosetests testlib.test_data:TestFilter      # Only run the TestFilter class
nosetests testlib.test_data:TestFilter.test_get_engine      # Run a single method
```

## Update Gramex Community Edition

In the gramex folder, create a branch for local development.

```bash
git checkout -b <branch-name>
```

Make your changes and check for build errors.

```bash
flake8                      # if you changed any .py files
eslint gramex/apps          # if you changed any .js files
python setup.py nosetests   # if you changed any functionality
```

On Windows, you may need to [enable Powershell scripts](http://stackoverflow.com/a/18533754/100904).

The tests take a long time. To test a subset, use `nosetests tests.<module>:<ClassName>.<method>`.

Commit your changes and push your branch:

```bash
git add .
git commit -m"Your detailed description of your changes."
git push --set-upstream origin <branch-name>
```

Submit a pull request to the [dev branch](http://github.com/gramener/gramex/tree/dev/).
If possible:

- Write unit tests
- Document Python docstrings
- Document the feature in the guide at `gramex/apps/guide/`

## Release Gramex Community Edition

Check [build errors](https://travis-ci.com/gramener/gramex).
Test the `dev` branch locally on Python 2.7 and 3.6:

```bash
PYTHON=/path/to/python2.7 make release-test
PYTHON=/path/to/python3.6 make release-test
```

Update the following and commit to `dev` branch:

- `cd gramex/apps/admin2/; yarn run build; cd ../../..`
- `cd gramex/apps/ui/; yarn upgrade; cd ../../..` -- upgrade UI components
- `gramex/apps/guide/release/1.xx/README.md` -- add guide release notes
    - `make stats` for code size stats
    - `make coverage` for test coverage stats (part of `make release-test`)
- `gramex/apps/guide/release/README.md` -- add release entry
- `gramex/release.json` -- update the version number
- `pkg/docker-py3/Dockerfile` -- update the version number
- `python gramex/apps/guide/search/search.py` to update search index
- `node gramex/apps/guide/search/searchindex.js` to update search index

Commit and push the `dev` branch to the server. **Ensure pipeline passes.**:

```bash
git commit -m"DOC: Add v1.x.x release notes"
git push                    # Push the dev branch
```

Merge with master, create an annotated tag and push the master branch:

```bash
git checkout master
git merge dev
git tag -a v1.x.x -m"One-line summary of features"
git push --follow-tags
git checkout dev            # Switch back to dev
git merge master
```

Deploy on [gramener.com](https://gramener.com/gramex-update/) and
[pypi](https://pypi.python.org/pypi/gramex):

```bash
# Push docs and coverage tests
make push-docs push-coverage
# Push to pypi
make push-pypi              # log in as gramener
```

Deploy [docker instance](https://hub.docker.com/r/gramener/gramex/):

```bash
export VERSION=1.x.x        # Replace with Gramex version
docker build https://github.com/gramener/gramex.git#master:pkg/docker-py3 -t gramener/gramex:$VERSION
docker tag gramener/gramex:$VERSION gramener/gramex:latest
docker login                # log in as sanand0 / pratapvardhan
docker push gramener/gramex
```

Re-start gramex on deployed servers.

## Release Gramex Enterprise Edition

Update the following and commit to `dev` branch:

- `setup.py` -- update the version number to the Gramex version number
- TODO: document CHANGELOG, etc.

Commit and push the `dev` branch to the server. **Ensure pipeline passes.**:

```bash
git commit -m"DOC: Add v1.x.x release notes"
git push                    # Push the dev branch
```

Merge with master, create an annotated tag and push the master branch:

```bash
git checkout master
git merge dev
git tag -a v1.x.x -m"One-line summary of features"
git push --follow-tags
git checkout dev            # Switch back to dev
git merge master
```

Deploy on [pypi](https://pypi.python.org/pypi/gramexenterprise):

```bash
rm -rf dist/
python setup.py sdist
# If this fails, add '-p PASSWORD'
twine upload -u gramener dist/*
```

Deploy [docker instance](https://hub.docker.com/r/gramener/gramex/):

```bash
export VERSION=1.x.x        # Replace with Gramex version
docker build https://github.com/gramener/gramex.git#master:pkg/docker-py3 -t gramener/gramex:$VERSION
docker tag gramener/gramex:$VERSION gramener/gramex:latest
docker login                # log in as sanand0 / pratapvardhan
docker push gramener/gramex
```

Re-start gramex on deployed servers.
