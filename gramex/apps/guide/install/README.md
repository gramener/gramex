title: Install Gramex

- Download and install [Anaconda][anaconda] 4.4.0 or later. [Update Anaconda][update] if required.
- On a Mac, download and install [Xcode][xcode].
- Run `pip install https://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master`.
  (Replace ``master`` with ``dev`` for the development version).
- Run `gramex` to start Gramex
- Press `Ctrl+C` to terminate Gramex.

Gramex runs at `http://127.0.0.1:9988/` and shows the Gramex Guide by default.
You may also run Gramex via `python -m gramex`.

If you are behind a HTTP proxy, use `pip install --proxy=http://{proxy-host}:{port} ...`.

[anaconda]: http://continuum.io/downloads
[update]: http://docs.continuum.io/anaconda/install#updating-from-older-anaconda-versions
[xcode]: https://developer.apple.com/xcode/download/
[gramex]: https://code.gramener.com/s.anand/gramex/repository/archive.tar.bz2?ref=master

[//]: # Note: pip install --ignore-installed was removed because of this Anaconda bug:
[//]: # https://github.com/pypa/pip/issues/2751#issuecomment-165390180
[//]: # However, this forces an upgrade of scandir which fails on Windows.

# Troubleshooting

If Gramex is does not run:

- Make sure Gramex 0.x (or any other module named `gramex`) is **NOT** in your
  `PYTHONPATH`. Run `python -c "import gramex;print gramex.__file__"` and confirm
  that this is where the latest Gramex was installed.
- Make sure that typing `gramex` runs the Gramex executable, and is not aliased
  to a different command.
- Try `python -m gramex` instead of `gramex`
- Tru uninstalling and re-installing Gramex. Stop Gramex and all other Python
  applications when re-installing.

# Uninstall Gramex

To remove Gramex, run `pip uninstall gramex`

# Offline install

First, do the following on a system **with an Internet connection**:

1. Create a folder called `offline`
2. Download [Anaconda][anaconda] into `offline`
3. Download [Gramex][gramex] into `offline` as `gramex.tar.bz2`
4. In the `offline` folder, run `pip download gramex.tar.bz2`

If you are behind a HTTP proxy, use `pip download --proxy=http://{proxy-host}:{port} ...`.

Copy the `offline` folder to the target machine (which need not have an Internet
connection). Then:

1. Install the [Anaconda][anaconda] executable
2. From the `offline` folder, run `pip install --no-index --find-links . gramex.tar.bz2`
