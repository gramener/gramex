Gramex
======

Gramex is an extensible data analytics and visualization platform for business.

Install
-------

.. _git: https://git-scm.com/
.. _Anaconda: http://continuum.io/downloads

Gramex is distributed via ``pip``. To install Gramex:

1. Install `git`_
2. Install `Anaconda`_.
3. Install Gramex. You can either install via SSH::

    pip install --upgrade git+ssh://git@code.gramener.com/s.anand/gramex.git@master

  ... or via HTTP, typing in your username and password::

    pip install --upgrade git+http://code.gramener.com/s.anand/gramex.git@master

The ``@master`` branch has the latest stable version. For the latest development
version, replace ``@master`` with ``@dev``.

Uninstall
~~~~~~~~~

To remove Gramex, run::

    pip uninstall gramex


Offline install
~~~~~~~~~~~~~~~

To install Gramex without an Internet connection:

1. Create a folder called ``offline``
2. Download `Anaconda`_ into ``offline``
3. Download Python modules by running::

    pip install --download /path/to/offline git+ssh://git@code.gramener.com/s.anand/gramex.git@master

On the target machine:

1. Install `Anaconda`_ from the ``offline`` folder
2. Install gramex using::

    pip install --no-index --find-links /path/to/offline gramex


Usage
-----

Run Gramex::

    gramex

Gramex runs at ``http://127.0.0.1:9988/`` and will show the current directory by
default.

You may also run Gramex via ``python -m gramex``.

For usage instructions, visit https://learn.gramener.com/gramex/


License
-------

This version of Gramex does not require a license.
