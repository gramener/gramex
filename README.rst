Gramex
======

Gramex is a declarative data analytics and visualization platform.


Setup
-----

Gramex is distributed internally via ``pip``. Install
`Anaconda <http://continuum.io/downloads>`__. Then::

    # Install via SSH
    pip install git+ssh://git@code.gramener.com/s.anand/gramex.git@master

    # ... or install via HTTP (and type your username + password)
    pip install git+http://code.gramener.com/s.anand/gramex.git@master

The ``@master`` branch has the latest stable version. For the latest development
version, use ``@dev`` instead of ``@master``.

Run Gramex::

    gramex

Gramex runs at ``http://127.0.0.1:8888/`` and will show the current directory by
default.
