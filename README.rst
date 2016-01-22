.. |Gramex| replace:: Gramex |version|

Gramex
======

Gramex is an extensible data analytics and visualization platform for business.

Install
-------

.. _Anaconda: http://continuum.io/downloads
.. _Gramex: https://learn.gramener.com/downloads/release/gramex-1.0.3.zip
.. _update Anaconda: http://docs.continuum.io/anaconda/install#updating-from-older-anaconda-versions
.. _XCode: https://developer.apple.com/xcode/download/

On **Linux**, run this command to set up Gramex (replace ``master`` with ``dev`` for
the development version)::

    source <(wget -qO- http://code.gramener.com/s.anand/gramex/raw/master/setup.sh)

On **Windows or Mac**:

1. Download and install `Anaconda`_ (2.4.1 or later -- `update Anaconda`_ if required)
2. On a Mac, download and install `XCode`_
3. Run ``pip install --upgrade --ignore-installed http://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master``
   (replace ``master`` with ``dev`` for the development version)

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

### Troubleshooting

If Gramex is not running:

- Make sure that typing ``gramex`` runs the |Gramex| executable, and is
  not aliased to a different command.
- Make sure Gramex 0.x (or any other module named ``gramex``) is **NOT** in your
  ``PYTHONPATH``. Run ``python -c "import gramex;print gramex.__file__"`` and
  confirm that this is where the latest Gramex was installed.

License
-------

|Gramex| does not require a license.
