.. |Gramex| replace:: Gramex |version|

Gramex
======

Gramex is an extensible data analytics and visualization platform for business.

Install
-------

.. _Anaconda: https://continuum.io/downloads
.. _Update Anaconda: https://docs.continuum.io/anaconda/install#updating-from-older-anaconda-versions
.. _Xcode: https://developer.apple.com/xcode/download/

1. Download and install `Anaconda`_ 4.4.0 or later. `Update Anaconda`_ if required
2. **Only on Mac**, download and install `Xcode`_. Then run ``conda install -c gramener watchdog``.
3. Run ``pip install https://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master``
   (replace ``master`` with ``dev`` for the development version).

.. Note: pip install --ignore-installed was removed because of this Anaconda bug:
.. https://github.com/pypa/pip/issues/2751#issuecomment-165390180
.. However, this forces an upgrade of scandir which fails on Windows.

Uninstall
~~~~~~~~~

To remove Gramex, run::

    pip uninstall gramex


Offline install
~~~~~~~~~~~~~~~

.. _Gramex: https://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master

To install Gramex without an Internet connection:

1. Create a folder called ``offline``
2. Download `Anaconda`_ into ``offline``
3. Download |Gramex|_ into ``offline`` as ``gramex.tar.bz2``
4. In the ``offline`` folder, run ``pip download gramex.tar.bz2``

On the target machine:

1. Install `Anaconda`_ from the ``offline`` folder
2. Install gramex using::

    pip install --no-index --find-links /path/to/offline gramex.tar.bz2


Usage
-----

Run Gramex::

    gramex

Gramex runs at ``http://127.0.0.1:9988/`` and will show the current directory by
default. You may also run Gramex via ``python -m gramex``.

For usage instructions, visit https://learn.gramener.com/gramex/

If Gramex is not running:

- Make sure that typing ``gramex`` runs the |Gramex| executable, and is
  not aliased to a different command.
- Make sure Gramex 0.x (or any other module named ``gramex``) is **NOT** in your
  ``PYTHONPATH``. Run ``python -c "import gramex;print gramex.__file__"`` and
  confirm that this is where the latest Gramex was installed.

Press Ctrl+C to terminate Gramex.


License
-------

|Gramex| does not require a license.
