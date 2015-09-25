Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Discussion
~~~~~~~~~~

To follow changes on the project, ask one of the :doc:`authors` to add you
as a reporter to this project.

Report Bugs
~~~~~~~~~~~

Report bugs at http://code.gramener.com/sanand/gramex/issues.

If you are reporting a bug, please include:

* Your operating system and browser -- name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitLab issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitLab issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

Gramex could always use more documentation, whether as part of the
official Gramex docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at
http://code.gramener.com/s.anand/gramex/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Building Gramex
---------------

- The `master <http://code.gramener.com/s.anand/gramex/tree/master/>`__ branch
  holds the latest stable version.
- The `dev <http://code.gramener.com/s.anand/gramex/tree/dev/>`__ branch has the
  latest development version
- Any other branches are temporary feature branches


Gramex runs on Python 2.7+ and Python 3.4+ in Windows and Linux.
To set up the development environment:

1. Install `Anaconda <http://continuum.io/downloads>`__ and
   `git <https://git-scm.com/>`__.
2. Fork the `Gramex repo <https://code.gramener.com/s.anand/gramex>`__
3. Clone your fork locally::

    git clone git@code.gramener.com:your_user_id/gramex.git

4. In the gramex folder, create a branch for local development::

    cd gramex
    git checkout -b <branch-name>

   Now you can make your changes locally.

5. Install this branch in editable mode. This "installs" the gramex folder in
   development mode. Changes to this folder are reflected in the environment::

    pip install -e .

5. Install development requirements::

    pip install -r gramex/requirements.txt
    pip install -r gramex/dev-requirements.txt

6. When you're done making changes, check that your changes pass flake8 and the
   tests, as well as provide reasonable test coverage::

    make release-test

   To run a subset of tests::

    python -m unittest tests.test_gramex

   **Note**: This uses the ``python.exe`` in your ``PATH``. To change the Python
   used, run::

    export PYTHON=/path/to/python         # e.g. path to Python 3.4+

7. Commit your changes and push your branch::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push --set-upstream origin <branch-name>

7. Submit a pull request through the code.gramener.com website.

8. To delete your branch::

    git branch -d <branch-name>
    git push origin --delete <branch-name>

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 2.7 and 3.4.

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

1. Test the release by running::

    export PYTHON=/path/to/python2.7
    make test-release
    export PYTHON=/path/to/python3.4
    make test-release

2. Update ``__version__ = 1.x.x`` in :mod:`gramex` and commit.

3. Create an annotated tag and push the code::

    git tag -a v1.x.x
    git push --follow-tags

Release plan
------------

Version 1.0.2
~~~~~~~~~~~~~

- ``<vega-chart>`` spec as open source npm package
    - Definition:
        - ``<vega-chart src="">...json...</vegachart>``.
          Use ``src`` attribute (not ``href`` -- see `link vs src`_)
        - Embedded JSON overrides ``src`` spec via .update()
    - No API to update the spec. Just expose the objects. To completely redraw,
      replace the DOM element.
    - How to bundle dependencies?
        - https://github.com/jsdelivr/jsdelivr
        - https://github.com/cdnjs/cdnjs
    - Check with @jheer and @arvind -- get their blessings
- How to bundle this with Gramex?

.. _link vs src: http://stackoverflow.com/a/7794936/100904

Version 1.0.3
~~~~~~~~~~~~~

- Data handler that provides connectivity to databases, files, etc. via odo

Version 1.0.4
~~~~~~~~~~~~~

- Sample datasets
- Gallery

Features in future releases
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- :func:`gramex.handlers.TransformHandler`:
    - Write test cases
    - Cache the transformed result based on the file / directory stat
    - Allow ``default_filename`` and ``path`` to be a list. The handler searches
      the paths and files one by one and renders the first match.
- In :mod:`gramex.transforms` write a template transform that renders Tornado
  templates.


Project plan
------------

**Bold dates** indicate milestones.

- **Mon 31 Aug**: Begin Gramex 1.0. **Status: done, on time**
- **Fri 4 Sep**: Core server spec and prototype release. **Status: done, on time**
- **Mon 14 Sep**: Handler and component spec. **Status: done, on time**
- **Mon 21 Sep**: Revised handler and component spec and prototype.
  Components listed. **Status: delayed**
- **Mon 28 Sep**: `Version 1.0.2`_
- **Mon 5 Oct**: `Version 1.0.3`_ and `Version 1.0.4`_
- **Mon 26 Oct**: Spec freeze. Components early release
- **Mon 9 Nov**: Gramex 1.0 beta release to testing. Start bugfixing
- **Mon 23 Nov**: Gramex 1.0 release
