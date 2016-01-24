Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

.. _issues page: http://code.gramener.com/sanand/gramex/issues

- **Discussion**: To follow changes on the project, ask one of the
  :doc:`authors` to add you as a reporter to this project.
- **Report bugs** on the `issues page`_. Please include:
    - Your operating system and browser -- name and version.
    - Any details about your local setup that might be helpful in troubleshooting.
    - Detailed steps to reproduce the bug.
- **Fix bugs**. Look through the `issues page`_ for bugs. Anything tagged with
  "bug" is open to whoever wants to implement it.
- **Implement features**. Look through the `issues page`_ for features. Anything
  tagged with "feature" is open to whoever wants to implement it.
- **Write documentation**. Gramex could always use more documentation, whether
  as part of the official Gramex docs, in docstrings, or even on the web in blog
  posts, articles, and such.
- **Submit Feedback**: The best way to send feedback is to file an issue on the
  `issues page`_. If you are proposing a feature, explain in detail how it would
  work, and keep the scope as narrow as possible to make it easier to implement.

Building Gramex
---------------

- The `master <http://code.gramener.com/s.anand/gramex/tree/master/>`__ branch
  holds the latest stable version.
- The `dev <http://code.gramener.com/s.anand/gramex/tree/dev/>`__ branch has the
  latest development version
- Any other branches are temporary feature branches


Gramex runs on Python 2.7+ and Python 3.4+ in Windows and Linux.
To set up the development environment on Ubuntu, run this script::

    source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup-dev.sh)

To manually set up the development environment, follow these steps.

1. Install `Anaconda <http://continuum.io/downloads>`__ (version 2.4 or higher)
2. Install `node.js <https://nodejs.org/>`__. Then install `bower <http://bower.io/>`__::

      npm install -g bower

3. Install `git` and `make`. On Windows, use
   `git <https://git-scm.com/>`__ and
   `make <http://gnuwin32.sourceforge.net/packages/make.htm>`__, or use
   `cygwin <https://cygwin.com/install.html>`__.
4. Optionally, to create PDF documentation, install
   `MiKTeX <http://miktex.org/>`__ and add it to your PATH
5. Fork the `Gramex repo <https://code.gramener.com/s.anand/gramex>`__
6. Clone your fork locally::

      git clone git@code.gramener.com:your_user_id/gramex.git
      (OR)
      git clone http://code.gramener.com/your_user_id/gramex.git

   ... and change to the ``gramex`` folder::

      cd gramex

7. Install development requirements, and also this branch in editable mode. This
   "installs" the gramex folder in development mode. Changes to this folder are
   reflected in the environment::

      pip install -r requirements.txt         # Base requirements
      pip install -r requirements-dev.txt     # Additional development requirements
      pip uninstall gramex                    # Uninstall any previous gramex repo
      pip install -e .                        # Install this repo as gramex

8. Install bower components::

      bower install

   This requires SSH keys to be set up for github.com and code.gramener.com. If
   your SSH keys are not set up, or you prefer to **always use https** instead,
   type this::

      git config url."https://".insteadOf "git://"

Contributing to Gramex
----------------------

1. In the gramex folder, create a branch for local development::

      git checkout -b <branch-name>

   Now you can make your changes locally.

2. When you're done making changes, check that your changes pass flake8 and the
   tests, as well as provide reasonable test coverage::

        make release-test

   To run a subset of tests::

        python -m unittest tests.test_gramex

   **Note**: This uses the ``python.exe`` in your ``PATH``. To change the Python
   used, run::

      export PYTHON=/path/to/python         # e.g. path to Python 3.4+

3. Commit your changes and push your branch::

      $ git add .
      $ git commit -m "Your detailed description of your changes."
      $ git push --set-upstream origin <branch-name>

4. Submit a pull request through the code.gramener.com website.

5. To delete your branch::

      git branch -d <branch-name>
      git push origin --delete <branch-name>

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 2.7, 3.4 and 3.5

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

1. Test the ``dev`` branch by running::

    export PYTHON=/path/to/python2.7
    make release-test
    export PYTHON=/path/to/python3.4
    make release-test

2. Build and upload the release::

    make release

3. Update the following and commit:
    - ``docs/HISTORY.rst`` -- add release notes
    - ``README.rst`` -- update the version number
    - ``gramex/release.json`` -- update the version number

4. Merge with master, create an annotated tag and push the code::

    git checkout master
    git merge dev
    git tag -a v1.x.x           # Annotate with a one-line summary of features
    git push --follow-tags
