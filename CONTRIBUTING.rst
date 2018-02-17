Contributing
============

Building Gramex
---------------

- The `master <http://code.gramener.com/s.anand/gramex/tree/master/>`__ branch
  holds the latest stable version.
- The `dev <http://code.gramener.com/s.anand/gramex/tree/dev/>`__ branch has the
  latest development version
- All other branches are temporary feature branches


Gramex can be developed on Python 2.7, 3.4 and 3.5 on Windows or Linux.
To set up the development environment:

1. Download and install `Anaconda`_ 4.0.0 or later -- `update Anaconda`_ if required
2. Install databases and support packages. On Windows, install ``git``,
   ``make``, PostgreSQL and MySQL. On Linux::

      $ sudo apt-get install -y git make sqlite3 postgresql postgresql-contrib libpq-dev python-dev
      $ DEBIAN_FRONTEND=noninteractive apt-get -y -q install mysql-server

3. Clone the dev branch and install it::

      $ git clone -b dev git@code.gramener.com:s.anand/gramex.git gramex
      $ pip install -e gramex

.. _Anaconda: http://continuum.io/downloads
.. _update Anaconda: http://docs.continuum.io/anaconda/install#updating-from-older-anaconda-versions


Contributing to Gramex
----------------------

1. In the gramex folder, create a branch for local development::

      git checkout -b <branch-name>

   Now you can make your changes locally.

2. When you're done making changes, run flake8, unit tests and coverage.
   On Windows, you may need to [enable Powershell scripts](http://stackoverflow.com/a/18533754/100904).
   (To run a subset of tests, use ``... nosetests tests.test_gramex``)::

      pip install -q -e .
      flake8
      python setup.py nosetests

3. Commit your changes and push your branch::

      $ git add .
      $ git commit -m "Your detailed description of your changes."
      $ git push --set-upstream origin <branch-name>

4. Submit a pull request through the code.gramener.com website. Make sure you:

    - Write unit tests
    - Document the feature in docstrings
    - Explain how to use the feature in ``docs/``
    - Test on Python 2.7, 3.4 and 3.5


Gramex documentation
--------------------

Gramex documentation is hosted at https://learn.gramener.com/gramex/. To set
this up:

1. Add the ``ec2@gramener.com`` SSH key as a
   `deploy key <http://code.gramener.com/s.anand/gramex/deploy_keys>`_
2. Add ``https://gramener.com/hook/`` as a
   `web hook <http://code.gramener.com/s.anand/gramex/hooks>`_
3. In https://gramener.com/hook/ go to Paths and add a hook:
   - url: ``git@code.gramener.com:s.anand/gramex.git``
   - folder: ``/mnt/gramener/apps/gramex/``
   - command: ``make docs``
4. ``ssh learn.gramener.com`` and run::

    cd /mnt/gramener/apps/gramex      # Go to the Gramex folder
    git checkout dev                  # Check out the dev branch
    pip install -r requirements.txt   # install dependencies

    # Link the docs under https://learn.gramener.com/gramex/
    cd /mnt/gramener/learn.gramener.com
    ln -s /mnt/gramener/apps/gramex/docs/_build/html


Release
-------

When releasing a new version of Gramex:

1. Check `build errors <http://code.gramener.com/s.anand/gramex/builds>`__.
   Test the ``dev`` branch on Python 2.7 and 3.6::

    PYTHON=/path/to/python2.7 make release-test
    PYTHON=/path/to/python3.6 make release-test

2. Update the following and commit to ``dev`` branch:

    - ``HISTORY.rst``
      - add release notes
      - add test coverage % (``make coverage``)
      - add code base using (``make stats``)
    - ``gramex/release.json`` -- update the version number
    - ``pkg/docker-py3/Dockerfile`` -- update the version number
    - Run ``python gramex/apps/guide/search/search.py`` using Python 3
    - Run ``node gramex/apps/guide/search/searchindex.json``

3. Commit and push the ``dev`` branch to the server. Merge with master, create
   an annotated tag and push the master branch::

    git commit -m"DOC: Add v1.x.x release notes"
    git push                    # Push the dev branch
    git checkout master
    git merge dev
    git tag -a v1.x.x           # Annotate with a one-line summary of features
    git push --follow-tags
    git checkout dev            # Switch back to dev

5. Deploy on gramener.com::

    # Push states
    make push-docs push-coverage
    # Restart Gramex at port 9988 on gramener.com

6. Deploy docker instances::

    export VERSION=1.x.x        # Replace with Gramex version
    docker build https://code.gramener.com/s.anand/gramex.git#master:pkg/docker-py3 -t gramener/gramex:$VERSION
    docker tag gramener/gramex:$VERSION gramener/gramex:latest
    docker login                # log in as sanand0
    docker push gramener/gramex
