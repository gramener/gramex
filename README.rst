Gramex
======

Gramex is an extensible data analytics and visualization platform for business.

Installation
------------

.. _git: https://git-scm.com/
.. _Anaconda: http://continuum.io/downloads

Gramex is distributed via ``pip``. Install `git`_ and `Anaconda`_. Then::

    # Install via SSH
    pip install git+ssh://git@code.gramener.com/s.anand/gramex.git@master

    # ... or install via HTTP (and type your username + password)
    pip install git+http://code.gramener.com/s.anand/gramex.git@master

The ``@master`` branch has the latest stable version. For the latest development
version, use ``@dev`` instead of ``@master``.

To upgrade an existing installation, run ``pip install --upgrade`` instead of
``pip install``.

Usage
-----

Run Gramex::

    gramex

Gramex runs at ``http://127.0.0.1:9988/`` and will show the current directory by
default.

You may also run Gramex via ``python -m gramex``.

For usage instructions, visit https://learn.gramener.com/gramex/
