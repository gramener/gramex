Building
========

Environment
-----------

Gramex runs on Python 2.7+ and Python 3.4+ in Windows and Linux.
To set up the development environment, install
`Anaconda <http://continuum.io/downloads>`__ and
`git <https://git-scm.com/>`__. Then run::

    git clone git@code.gramener.com:s.anand/gramex.git
    pip install -r gramex/requirements.txt
    pip install -r gramex/dev-requirements.txt

Branches
--------

- The `master <http://code.gramener.com/s.anand/gramex/tree/master/>`__ branch
  holds the latest stable version.
- The `dev <http://code.gramener.com/s.anand/gramex/tree/dev/>`__ branch has the
  latest development version
- Any other branches are temporary feature branches

To create a branch::

    git checkout -b <branchname>
    git push --set-upstream origin <branchname>

To delete a branch::

    git branch -d <branchname>
    git push origin --delete <branchname>

Release
-------

To make a new release, run this command. It should not report errors, and
should provide satisfactory test coverage::

    make release-test

**Note**: This uses the ``python.exe`` in your ``PATH``. To change the Python
used, run::

    export PYTHON=/path/to/python.exe       # e.g. path to Python 3.4+

Update ``__version__ = 1.x.x`` in ``gramex/__init__.py`` and commit.

Create an annotated tag and push the code::

    git tag -a v1.x.x
    git push --follow-tags
