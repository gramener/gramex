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

4. Create a branch for local development::

    git checkout -b <branch-name>

   Now you can make your changes locally.

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

Release
-------

When releasing a new version of Gramex:

1. Test the release by running::

    make test-release

2. Update ``__version__ = 1.x.x`` in :mod:`gramex` and commit.

3. Create an annotated tag and push the code::

    git tag -a v1.x.x
    git push --follow-tags

Features you can take up
------------------------

These are planned features that we need help with.

- :func:`gramex.handlers.TransformHandler`:
    - Write test cases
    - Cache the transformed result based on the file / directory stat
    - Allow ``default_filename`` and ``path`` to be a list. The handler searches
      the paths and files one by one and renders the first match.
- In :mod:`gramex.transforms` write a template transform that renders Tornado
  templates.

Project plan
------------

**Bold dates** indicate milestones. *Italic dates* indicate plans.
Normal dates indicate actual activity.

- **Mon 31 Aug**: Begin Gramex 1.0. **Status: done, on time**
- Mon 31 Aug: Define Gramex config syntax, logging and scheduling
  services
- Tue 1 Sep: Define config layering, error handling, component
  requirements
- Wed 2 Sep: Build prototype. Explore component approach. Share project
  plan
- Thu 3 Sep: Add config, scehduler and logger services. Explore
  component approach
- Fri 4 Sep: Core server ready for release.
- **Fri 4 Sep**: Core server spec and prototype release. **Status: done, on time**
- Mon 7 Sep: Explore Vega, dask
- Tue 8 Sep: Add DirectoryHandler, 1.0.0 release
- Wed 9 Sep: Update documentation
- **Mon 14 Sep**: Handler and component spec. **Status: done, on time**
- Mon 14 Sep: Explore web components
- Tue 15 Sep: Create an XML - data interconversion engine
- Thu 17 Sep: create examples of Vega charts
- Fri 18 Sep: Write high-level collateral on technology stack direction:
  Tornado, Blaze, node, Vega, Web components
- Sat 19 Sep: create a HTML - YAML interconverter handler. This will be the
  primary templating handler we will use using ``<vega-chart>``
- Sun 19 Sep: create ``<vega-chart>`` webcomponents
- **Mon 21 Sep**: Revised handler and component spec and prototype.
  Components listed. **Status: delayed**
- Mon 21 Sep 2015: Create gallery of vega components. Create TransformHandler
- Tue 22 Sep 2015: Extend the component gallery.
- Wed 23 Sep 2015: Extend the component gallery. Create BadgerFish transform
- Thu 24 Sep 2015: Finalise ``<vega-chart>`` API
- *Wed 23 Sep 2015*: Create at least 5 full demo dashboards. Use it to identify server-side needs
- *Thu 24 Sep 2015*: Define and start implementing server-side interface (data, templating)
- *Fri 25 Sep 2015*: Data and template handlers
- **Mon 28 Sep**: Data handler working with charts
- **Mon 5 Oct**: Add ``<vega-lite>`` and more components. Document specs
- **Mon 26 Oct**: Spec freeze. Components early release
- **Mon 9 Nov**: Gramex 1.0 beta release to testing. Start bugfixing
- **Mon 23 Nov**: Gramex 1.0 release
