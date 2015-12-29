.. |Gramex| replace:: Gramex |version|

Gramex
======

Gramex is an extensible data analytics and visualization platform for business.

Install
-------

.. _Anaconda: http://continuum.io/downloads
.. _Gramex: https://learn.gramener.com/downloads/release/gramex-1.0.3.zip

1. Download and install `Anaconda`_.
2. Download |Gramex|_
3. Install by typing ``pip install gramex-1.0.3.zip``

To set up the master branch, run::

    source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup.sh)

Uninstall
~~~~~~~~~

To remove Gramex, run::

    pip uninstall gramex


Offline install
~~~~~~~~~~~~~~~

To install Gramex without an Internet connection:

1. Create a folder called ``offline``
2. Download `Anaconda`_ into ``offline``
3. Download |Gramex|_ into ``offline``
4. In the ``offline`` folder, run ``pip install --download . gramex-1.0.3.zip``

On the target machine:

1. Install `Anaconda`_ from the ``offline`` folder
2. Install gramex using::

    pip install --no-index --find-links /path/to/offline gramex


Usage
-----

Run Gramex::

    gramex

Gramex runs at ``http://127.0.0.1:9988/`` and will show the current directory by
default. You may also run Gramex via ``python -m gramex``.

For usage instructions, visit https://learn.gramener.com/gramex/

If this does not work:

- Make sure that typing ``gramex`` runs the |Gramex| executable, and is
  not aliased to a different command
- Make sure no other packages or modules named ``gramex`` are in your
  ``PYTHONPATH`` environment variable

License
-------

|Gramex| does not require a license.
